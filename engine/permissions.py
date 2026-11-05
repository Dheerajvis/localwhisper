import sys
import time

def check_and_request_permissions() -> dict:
    """
    Checks and prompts for macOS Microphone and Accessibility permissions on startup.
    Prompts once natively if not determined, and never prompts again once granted.
    """
    results = {"microphone": True, "accessibility": True}
    
    if sys.platform != "darwin":
        return results

    # 1. Microphone Permission Check (AVFoundation)
    try:
        from AVFoundation import AVCaptureDevice, AVMediaTypeAudio
        # Status: 0=NotDetermined, 1=Restricted, 2=Denied, 3=Authorized
        status = AVCaptureDevice.authorizationStatusForMediaType_(AVMediaTypeAudio)
        print(f"[Permissions] Microphone Authorization Status: {status}", flush=True)

        if status == 3:
            # Already authorized - do nothing!
            results["microphone"] = True
        elif status == 0:
            # First launch: prompt user natively once
            print("[Permissions] Requesting Microphone access once...", flush=True)
            granted_box = [None]
            def callback(granted):
                granted_box[0] = granted
                print(f"[Permissions] Microphone prompt response: {granted}", flush=True)
            AVCaptureDevice.requestAccessForMediaType_completionHandler_(AVMediaTypeAudio, callback)
            
            for _ in range(10):
                if granted_box[0] is not None:
                    break
                time.sleep(0.1)
            results["microphone"] = (granted_box[0] is True or status == 3)
        else:
            print("[Permissions] Microphone permission not authorized in System Settings.", flush=True)
            results["microphone"] = False
    except Exception as e:
        print(f"[Permissions] Microphone check notice: {e}", flush=True)

    # 2. Accessibility Permission Check (ApplicationServices)
    try:
        from ApplicationServices import AXIsProcessTrusted, AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt
        trusted = AXIsProcessTrusted()
        print(f"[Permissions] Accessibility Trusted: {trusted}", flush=True)

        if trusted:
            # Already trusted - do nothing!
            results["accessibility"] = True
        else:
            # Prompt user natively once with system dialog
            print("[Permissions] Triggering native Accessibility prompt once...", flush=True)
            options = {kAXTrustedCheckOptionPrompt: True}
            AXIsProcessTrustedWithOptions(options)
            results["accessibility"] = False
    except Exception as e:
        print(f"[Permissions] Accessibility check notice: {e}", flush=True)

    return results

if __name__ == "__main__":
    print(check_and_request_permissions())
