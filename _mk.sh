set -e
cd /mnt/c/Users/asalh/AppData/Local/Hermes/cache/scratch/demo/media
ffmpeg -y -f lavfi -i testsrc=size=320x240:rate=25:duration=3 -c:v libx264 -pix_fmt yuv420p _t_h264.mp4 -loglevel error
ffmpeg -y -f lavfi -i testsrc=size=320x240:rate=25:duration=3 -c:v libvpx-vp9 -b:v 300k _t_vp9.webm -loglevel error
ls -l _t_h264.mp4 _t_vp9.webm
