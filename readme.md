docker build -t api_web_leech_truyen_audio .

docker run -d --restart always -v /root/dir_api_web_leech_truyen_audio:/_app_/utils/download --name api_web_leech_truyen_audio -p 60074:60074 api_web_leech_truyen_audio

docker save -o api_web_leech_truyen_audio.tar api_web_leech_truyen_audio

docker load -i api_web_leech_truyen_audio.tar


docker exec -it api_web_leech_truyen_audio bash

python -m venv .venv

.venv\Scripts\activate

taskkill /F /IM python.exe

.\.venv\Scripts\Activate.ps1