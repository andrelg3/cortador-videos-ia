import os
import subprocess
from flask import Flask, request, jsonify, send_file
import yt_dlp

app = Flask(__name__)

# Diretório base do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = "/tmp"
COOKIES_PATH = os.path.join(BASE_DIR, "youtube-cookies.txt")

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "Cortador de Vídeo Online!"}), 200

@app.route('/cortar', methods=['POST'])
def cortar_video():
    data = request.json
    url_youtube = data.get("url")
    tempo_inicio = data.get("inicio")  # Formato "00:00:10"
    tempo_fim = data.get("fim")        # Formato "00:00:25"
    
    if not url_youtube or not tempo_inicio or not tempo_fim:
        return jsonify({"erro": "Parâmetros 'url', 'inicio' e 'fim' são obrigatórios."}), 400

    video_original = os.path.join(TEMP_DIR, "video_original.mp4")
    video_corte = os.path.join(TEMP_DIR, "corte_final.mp4")

    # Remove arquivos de testes anteriores se existirem
    for f in [video_original, video_corte]:
        if os.path.exists(f):
            try:
                os.remove(f)
            except Exception:
                pass

    try:
        # 1. Configurações de Download
        print(f"Baixando: {url_youtube}")
        ydl_opts = {
            'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
            'outtmpl': video_original,
            'merge_output_format': 'mp4',
            'quiet': True,
            'nocheckcertificate': True,
        }

        # Se o arquivo de cookies existir no repositório, aplica ele
        if os.path.exists(COOKIES_PATH):
            print("🍪 Usando arquivo de cookies para autenticação.")
            ydl_opts['cookiefile'] = COOKIES_PATH
        else:
            print("⚠️ Arquivo youtube-cookies.txt não foi encontrado no repositório.")

        # Realiza o download
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url_youtube])

        # 2. Executa o corte usando o FFmpeg nativo da nuvem
        print(f"Cortando de {tempo_inicio} a {tempo_fim}")
        comando = [
            'ffmpeg', '-y',
            '-ss', tempo_inicio,
            '-to', tempo_fim,
            '-i', video_original,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            video_corte
        ]
        subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 3. Envia o arquivo de vídeo cortado direto de volta para o n8n
        return send_file(video_corte, mimetype='video/mp4', as_attachment=True, download_name='corte.mp4')

    except Exception as e:
        print(f"Erro no processamento: {str(e)}")
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
