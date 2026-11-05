#define PY_SSIZE_T_CLEAN
#import <Foundation/Foundation.h>
#import <AVFoundation/AVFoundation.h>
#import <ApplicationServices/ApplicationServices.h>
#import <Cocoa/Cocoa.h>
#include <Python.h>
#include <unistd.h>

int main(int argc, char *argv[]) {
    // 1. If this is a multiprocessing helper process (e.g. -c from multiprocessing...):
    if (argc > 1 && strcmp(argv[1], "-c") == 0) {
        @autoreleasepool {
            // Hide helper from Dock completely
            [NSApplication sharedApplication];
            [NSApp setActivationPolicy:NSApplicationActivationPolicyProhibited];
        }
        
        wchar_t **w_argv = (wchar_t **)malloc(argc * sizeof(wchar_t *));
        for (int i = 0; i < argc; i++) {
            w_argv[i] = Py_DecodeLocale(argv[i], NULL);
        }
        int ret = Py_Main(argc, w_argv);
        for (int i = 0; i < argc; i++) {
            PyMem_RawFree(w_argv[i]);
        }
        free(w_argv);
        return ret;
    }

    // 2. Main LocalWhisper Application
    @autoreleasepool {
        // Setup Logging to ~/Library/Logs/LocalWhisper.log
        NSString *homeDir = NSHomeDirectory();
        NSString *logsDir = [homeDir stringByAppendingPathComponent:@"Library/Logs"];
        [[NSFileManager defaultManager] createDirectoryAtPath:logsDir withIntermediateDirectories:YES attributes:nil error:nil];
        NSString *logPath = [logsDir stringByAppendingPathComponent:@"LocalWhisper.log"];
        
        freopen([logPath UTF8String], "a+", stdout);
        freopen([logPath UTF8String], "a+", stderr);

        NSLog(@"[LocalWhisper] Starting native app (PID: %d)", getpid());

        // 3. Microphone: Prompt ONLY if status is NotDetermined (first launch only)
        AVAuthorizationStatus micStatus = [AVCaptureDevice authorizationStatusForMediaType:AVMediaTypeAudio];
        NSLog(@"[LocalWhisper] Microphone permission status: %ld (3=Authorized)", (long)micStatus);
        if (micStatus == AVAuthorizationStatusNotDetermined) {
            NSLog(@"[LocalWhisper] First launch: Requesting microphone permission...");
            dispatch_semaphore_t sem = dispatch_semaphore_create(0);
            [AVCaptureDevice requestAccessForMediaType:AVMediaTypeAudio completionHandler:^(BOOL granted) {
                NSLog(@"[LocalWhisper] Microphone granted response: %d", granted);
                dispatch_semaphore_signal(sem);
            }];
            dispatch_semaphore_wait(sem, dispatch_time(DISPATCH_TIME_NOW, 10 * NSEC_PER_SEC));
        }

        // 4. Accessibility: Prompt if not yet trusted. Once granted, never prompts again.
        if (!AXIsProcessTrusted()) {
            NSLog(@"[LocalWhisper] Accessibility not yet granted. Triggering native prompt...");
            NSDictionary *opts = @{(__bridge id)kAXTrustedCheckOptionPrompt: @YES};
            AXIsProcessTrustedWithOptions((__bridge CFDictionaryRef)opts);
        } else {
            NSLog(@"[LocalWhisper] Accessibility already granted and trusted.");
        }

        // 5. Set Process Name to LocalWhisper
        [[NSProcessInfo processInfo] setProcessName:@"LocalWhisper"];

        // 6. Setup Embedded Python Runtime (Dynamically resolved)
        NSString *projectDir = [[[NSProcessInfo processInfo] environment] objectForKey:@"LOCALWHISPER_HOME"];
        if (!projectDir || [projectDir length] == 0) {
#ifdef PROJECT_DIR_DEF
            NSString *compiledDir = @(PROJECT_DIR_DEF);
            if ([compiledDir length] > 0 && [[NSFileManager defaultManager] fileExistsAtPath:[compiledDir stringByAppendingPathComponent:@"app.py"]]) {
                projectDir = compiledDir;
            }
#endif
            if (!projectDir) {
                NSString *resPath = [[NSBundle mainBundle] resourcePath];
                if ([[NSFileManager defaultManager] fileExistsAtPath:[resPath stringByAppendingPathComponent:@"app.py"]]) {
                    projectDir = resPath;
                } else {
                    projectDir = [[NSFileManager defaultManager] currentDirectoryPath];
                }
            }
        }

        NSString *venvSitePackages = [projectDir stringByAppendingPathComponent:@".venv/lib/python3.9/site-packages"];
        if (![[NSFileManager defaultManager] fileExistsAtPath:venvSitePackages]) {
            NSString *venvLib = [projectDir stringByAppendingPathComponent:@".venv/lib"];
            NSArray *libs = [[NSFileManager defaultManager] contentsOfDirectoryAtPath:venvLib error:nil];
            for (NSString *sub in libs) {
                if ([sub hasPrefix:@"python3."]) {
                    NSString *candidate = [venvLib stringByAppendingPathComponent:[sub stringByAppendingPathComponent:@"site-packages"]];
                    if ([[NSFileManager defaultManager] fileExistsAtPath:candidate]) {
                        venvSitePackages = candidate;
                        break;
                    }
                }
            }
        }
        
        chdir([projectDir UTF8String]);
        setenv("PYTHONUNBUFFERED", "1", 1);
        setenv("PYTHONIOENCODING", "UTF-8", 1);

        wchar_t *progName = Py_DecodeLocale(argv[0], NULL);
        if (progName) {
            Py_SetProgramName(progName);
        }

        Py_Initialize();

        NSString *bootstrapCode = [NSString stringWithFormat:
            @"import sys, os\n"
            @"sys.executable = '%s'\n"
            @"sys.path.insert(0, '%@')\n"
            @"sys.path.insert(0, '%@')\n"
            @"import app\n"
            @"app.LocalWhisperApp().run()\n",
            argv[0], venvSitePackages, projectDir
        ];

        int ret = PyRun_SimpleString([bootstrapCode UTF8String]);
        Py_Finalize();
        if (progName) {
            PyMem_RawFree(progName);
        }
        return ret;
    }
}
