import os
import subprocess
from flask import Flask, request, jsonify, send_file
import yt_dlp

app = Flask(__name__)

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

    # Usamos extensões genéricas durante o download temporário
    video_original = os.path.join(TEMP_DIR, "video_original")
    video_corte = os.path.join(TEMP_DIR, "corte_final.mp4")

    # Limpa arquivos de execuções anteriores
    for f in os.listdir(TEMP_DIR):
        if f.startswith("video_original") or f == "corte_final.mp4":
            try:
                os.remove(os.path.join(TEMP_DIR, f))
            except Exception:
                pass

    try:
        # 1. Baixa no formato mais compatível disponível (sem forçar MP4 rígido no download)
        print(f"Baixando: {url_youtube}")
        ydl_opts = {
            'format': 'best',  # Baixa o melhor formato unificado pré-existente
            'outtmpl': video_original + '.%(ext)s',
            'quiet': True,
            'nocheckcertificate': True,
        }

        if os.path.exists(COOKIES_PATH):
            print("🍪 Usando arquivo de cookies para autenticação.")
            ydl_opts['cookiefile'] = COOKIES_PATH

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url_youtube, download=True)
            # Descobre a extensão real do arquivo que foi baixado (ex: .mp4, .mkv, .webm)
            ext_real = info.get('ext', 'mp4')
            arquivo_baixado_real = f"{video_original}.{ext_real}"

        # 2. Executa o corte e converte/força a saída para MP4 compatível
        print(f"Cortando de {tempo_inicio} a {tempo_fim}")
        comando = [
            'ffmpeg', '-y',
            '-ss', tempo_inicio,
            '-to', tempo_fim,
            '-i', arquivo_baixado_real,
            '-c:v', 'libx264',   # Converte o vídeo para o padrão H.264 MP4
            '-c:a', 'aac',       # Converte o áudio para o padrão AAC
            '-strict', 'experimental',
            video_corte
        ]
        subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # 3. Devolve o arquivo cortado convertido em MP4
        return send_file(video_corte, mimetype='video/mp4', as_attachment=True, download_name='corte.mp4')

    except Exception as e:
        print(f"Erro no processamento: {str(e)}")
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
