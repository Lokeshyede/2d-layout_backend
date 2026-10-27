import imageio_ffmpeg
import subprocess
import os

def create_sample_mp4():
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    
    # We can take one of the recorded session webps or generate a high quality sample mp4
    src_webp = r"C:\Users\jayye\.gemini\antigravity-ide\brain\19228006-8222-49a5-b0f7-cd2fbbcdf34b\test_irregular_store_1790595343335.webp"
    dst_mp4 = r"e:\2d alyout\RetailFix_Store_Walkthrough_Sample.mp4"
    
    if os.path.exists(src_webp):
        cmd = [
            ffmpeg_exe,
            "-y",
            "-i", src_webp,
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "22",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            dst_mp4
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        print("FFmpeg return code:", res.returncode)
        if os.path.exists(dst_mp4):
            print(f"Sample MP4 created successfully at: {dst_mp4}, Size: {os.path.getsize(dst_mp4)} bytes")
        else:
            print("Stderr:", res.stderr)
    else:
        print("Source webp not found:", src_webp)

if __name__ == '__main__':
    create_sample_mp4()
