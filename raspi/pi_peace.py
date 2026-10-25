"""Pi Zero 2 W でピースを認識して、つないだディスプレイに映す（GUI なし）。

カメラは rpicam-vid から受け取り、画面は /dev/fb0 に直接描く。
MediaPipe 1.x は Pi Zero 2 W の CPU（AES 命令なし）で落ちるので、Python 3.12 + mediapipe 0.10.18 で動かす。
"""

import signal
import subprocess
import sys
import threading
import time
from math import acos, degrees, sqrt
from pathlib import Path

import cv2
import numpy as np

WIDTH, HEIGHT = 320, 240  # 認識に使う解像度。小さいほど速い
DISPLAY_FPS = 15  # 認識と分離し、カメラ映像は滑らかに更新する
DISPLAY_INTERVAL = 1 / DISPLAY_FPS
PHOTO_WIDTH, PHOTO_HEIGHT = 2592, 1944
COUNTDOWN_SECONDS = 3
MODEL = Path(__file__).parent / "models" / "hand_landmarker.task"
PHOTO_DIR = Path(__file__).parent / "photos"
SCREEN_W, SCREEN_H = (int(v) for v in Path("/sys/class/graphics/fb0/virtual_size").read_text().split(","))
ACCENT = (81, 0, 255)  # #ff0051（BGR）


def joint_angle(hand, mcp, pip, tip):
    """指の付け根・第2関節・指先が作る角度。手の表裏に左右されない。"""
    a = tuple(getattr(hand[mcp], axis) - getattr(hand[pip], axis) for axis in ("x", "y", "z"))
    b = tuple(getattr(hand[tip], axis) - getattr(hand[pip], axis) for axis in ("x", "y", "z"))
    length_a = sqrt(sum(value * value for value in a))
    length_b = sqrt(sum(value * value for value in b))
    if not length_a or not length_b:
        return 0
    cosine = sum(x * y for x, y in zip(a, b)) / (length_a * length_b)
    return degrees(acos(max(-1, min(1, cosine))))


def extended(hand, mcp, pip, tip):
    return joint_angle(hand, mcp, pip, tip) >= 150


def is_peace(hand):
    # 人差し指と中指が伸び、薬指と小指が曲がっている
    return extended(hand, 5, 6, 8) and extended(hand, 9, 10, 12) \
        and not extended(hand, 13, 14, 16) and not extended(hand, 17, 18, 20)


class Camera:
    """rpicam-vid の YUV420 出力を別スレッドで読み続け、最新の1枚だけ持つ（認識が遅くても遅延が溜まらない）。"""

    def __init__(self):
        self.control_lock = threading.Lock()
        self.latest = None
        self.process = None
        self._start()

    def _start(self):
        self.process = subprocess.Popen(
            ["rpicam-vid", "-t", "0", "-n", "--width", str(WIDTH), "--height", str(HEIGHT),
             "--framerate", "15", "--codec", "yuv420", "-o", "-"],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
        )
        threading.Thread(target=self._read, args=(self.process,), daemon=True).start()

    def _read(self, process):
        size = WIDTH * HEIGHT * 3 // 2
        while process is self.process \
                and (data := process.stdout.read(size)) and len(data) == size:
            yuv = np.frombuffer(data, np.uint8).reshape(HEIGHT * 3 // 2, WIDTH)
            frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR_I420)
            cv2.flip(frame, 1, dst=frame)  # 鏡のように左右反転
            self.latest = frame

    def read(self):
        return self.latest

    def _stop(self):
        process = self.process
        self.process = None
        if process and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()

    def capture_photo(self):
        """ライブ映像を一時停止し、最高解像度の JPEG を保存して再開する。"""
        PHOTO_DIR.mkdir(exist_ok=True)
        path = PHOTO_DIR / f"peace_{time.strftime('%Y%m%d_%H%M%S')}.jpg"
        with self.control_lock:
            self._stop()
            try:
                result = subprocess.run(
                    ["rpicam-still", "-n", "-t", "500", "--zsl", "--no-raw",
                     "--width", str(PHOTO_WIDTH), "--height", str(PHOTO_HEIGHT),
                     "-o", str(path)],
                    capture_output=True, text=True, timeout=15,
                )
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.strip() or "rpicam-still failed")
            finally:
                self._start()
        return path

    def stop(self):
        with self.control_lock:
            self._stop()


class Recognition:
    """重い手の認識を描画と別スレッドで実行し、最新結果だけを持つ。"""

    def __init__(self, camera, landmarker, mp):
        self.camera = camera
        self.landmarker = landmarker
        self.mp = mp
        self.latest = None
        self.countdown_started = None
        self.armed = True
        self.notice = None
        self.notice_until = 0
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self):
        while not self.stop_event.is_set():
            frame = self.camera.read()
            if frame is None:
                time.sleep(0.01)
                continue
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            image = self.mp.Image(image_format=self.mp.ImageFormat.SRGB, data=rgb)
            self.latest = self.landmarker.detect_for_video(image, int(time.monotonic() * 1000))
            peace_count = sum(is_peace(hand) for hand in self.latest.hand_landmarks)
            now = time.monotonic()

            if peace_count >= 2:
                if not self.armed:
                    continue
                if self.countdown_started is None:
                    self.countdown_started = now
                if now - self.countdown_started < COUNTDOWN_SECONDS:
                    continue

                self.armed = False
                self.countdown_started = None
                self.notice = "SHOOTING..."
                self.notice_until = float("inf")
                try:
                    path = self.camera.capture_photo()
                    print(f"saved: {path}", flush=True)
                    self.notice = "SAVED"
                except Exception as error:
                    print(f"capture failed: {error}", file=sys.stderr, flush=True)
                    self.notice = "ERROR"
                self.notice_until = time.monotonic() + 2
            else:
                self.countdown_started = None
                self.armed = True

    def stop(self):
        self.stop_event.set()
        self.thread.join(timeout=20)

    def status(self):
        if time.monotonic() < self.notice_until:
            return self.notice, None
        if self.armed and self.countdown_started is not None:
            elapsed = time.monotonic() - self.countdown_started
            return None, max(1, COUNTDOWN_SECONDS - int(elapsed))
        return None, None


def render_screen(frame, screen, resized):
    """画面の高さに合わせて拡大し、左右を黒で埋める。"""
    left = (SCREEN_W - resized.shape[1]) // 2
    screen.fill(0)
    cv2.resize(frame, (resized.shape[1], SCREEN_H), dst=resized)
    screen[:, left:left + resized.shape[1]] = resized


def write(fb, screen, pixels):
    cv2.cvtColor(screen, cv2.COLOR_BGR2BGR565, dst=pixels)
    fb.seek(0)
    fb.write(pixels)  # fb0 は 16bit（RGB565）


def put_centered_text(screen, text, scale, color, thickness):
    size, _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, scale, thickness)
    position = ((SCREEN_W - size[0]) // 2, (SCREEN_H + size[1]) // 2)
    cv2.putText(screen, text, position, cv2.FONT_HERSHEY_SIMPLEX, scale, color, thickness)


def main():
    signal.signal(signal.SIGTERM, lambda *_: sys.exit(0))  # 止められたら finally でカメラも閉じる
    fb = open("/dev/fb0", "r+b")
    display_width = WIDTH * SCREEN_H // HEIGHT
    screen = np.zeros((SCREEN_H, SCREEN_W, 3), np.uint8)
    resized = np.empty((SCREEN_H, display_width, 3), np.uint8)
    pixels = np.empty((SCREEN_H, SCREEN_W, 2), np.uint8)

    cv2.putText(screen, "LOADING...", (40, SCREEN_H // 2), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 4)
    write(fb, screen, pixels)

    # mediapipe の読み込みに 30 秒近くかかるので、先に LOADING を出してから読む
    import mediapipe as mp
    from mediapipe.tasks.python import BaseOptions, vision

    landmarker = vision.HandLandmarker.create_from_options(vision.HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=str(MODEL)),
        running_mode=vision.RunningMode.VIDEO,
        num_hands=2,
        min_hand_detection_confidence=0.4,
        min_hand_presence_confidence=0.4,
        min_tracking_confidence=0.4,
    ))
    camera = Camera()
    recognition = Recognition(camera, landmarker, mp)
    try:
        while True:
            started = time.monotonic()
            frame = camera.read()
            if frame is None:
                time.sleep(0.01)
                continue

            render_screen(frame, screen, resized)
            notice, countdown = recognition.status()
            if countdown is not None:
                put_centered_text(screen, str(countdown), 9, (255, 255, 255), 16)
            elif notice:
                put_centered_text(screen, notice, 2, ACCENT, 6)
            write(fb, screen, pixels)
            time.sleep(max(0, DISPLAY_INTERVAL - (time.monotonic() - started)))
    finally:
        recognition.stop()
        camera.stop()
        landmarker.close()
        fb.close()


if __name__ == "__main__":
    main()
