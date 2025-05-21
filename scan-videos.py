from ultralytics import YOLO
import cv2
import os
import sys
import datetime
import ffmpeg

# Check if a path is provided
if len(sys.argv) != 2:
    print("Usage: python scanvideo.py /path/to/videos")
    sys.exit(1)

# Load the model
model = YOLO("yolov8n.pt")  # Nano model for speed

# Get video directory from command line
video_dir = sys.argv[1]

# Generate output file name from path
output_file = video_dir.replace("/", "-").strip("-") + ".csv"
sample_interval = 10  # Analyze every 10 seconds

# Open output file with additional columns
with open(output_file, "w") as f:
    f.write("Video,Resolution,Length (s),Camera Type,Date Created,Tags\n")
    print(f"Scanning directory: {video_dir}")
    for video in os.listdir(video_dir):
        if video.endswith(".MP4"):
            full_path = os.path.join(video_dir, video)
            print(f"Processing: {video}")
            cap = cv2.VideoCapture(full_path)
            tags = set()
            if not cap.isOpened():
                print(f"Failed to open: {video}")
                continue
            
            # Extract video metadata from OpenCV
            fps = cap.get(cv2.CAP_PROP_FPS)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            length_seconds = frame_count / fps if fps > 0 else 0
            resolution = f"{width}x{height}"
            
            # Calculate frame skip for sampling
            frame_skip = int(fps * sample_interval)
            print(f"Video FPS: {fps}, Total frames: {frame_count}, Sampling every {frame_skip} frames")

            # Process video for tags
            current_frame = 0
            while cap.isOpened():
                ret, frame = cap.read()
                if not ret:
                    break
                if current_frame % frame_skip == 0:
                    results = model(frame)
                    for box in results[0].boxes:
                        cls_id = int(box.cls)
                        tag = results[0].names[cls_id]
                        tags.add(tag)
                current_frame += 1
            cap.release()

            # Infer date from filename (e.g., DJI_20240802161422_0005_D.MP4)
            try:
                date_str = video.split("_")[1]  # e.g., "20240802161422"
                date_created = datetime.datetime.strptime(date_str, "%Y%m%d%H%M%S").strftime("%Y-%m-%d %H:%M:%S")
            except (IndexError, ValueError):
                date_created = datetime.datetime.fromtimestamp(os.path.getctime(full_path)).strftime("%Y-%m-%d %H:%M:%S")

            # Get camera type from ffprobe encoder field
            try:
                probe = ffmpeg.probe(full_path)
                encoder = probe["streams"][0].get("codec_long_name", "Unknown")
                # Extract camera type from encoder (e.g., "DJI Avata" might be in there)
                camera_type = "Unknown"
                if "DJI" in encoder.upper():
                    camera_type = encoder.split("DJI")[1].strip() if "DJI" in encoder else "DJI"
                elif "DJI" in video:
                    camera_type = "DJI"  # Fallback to filename
            except (ffmpeg.Error, KeyError, IndexError):
                camera_type = "DJI" if "DJI" in video else "Unknown"

            # Write to CSV
            tag_str = ",".join(tags) if tags else "none"
            f.write(f"{video},{resolution},{length_seconds:.2f},{camera_type},{date_created},{tag_str}\n")
            print(f"Metadata for {video}: Resolution={resolution}, Length={length_seconds:.2f}s, Camera={camera_type}, Date={date_created}, Tags={tag_str}")
