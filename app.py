import os
import subprocess
import glob
from flask import Flask, request, jsonify, send_file
import yt_dlp

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = "/tmp"
COOKIES_PATH = os.path.join(BASE_DIR, "youtube-cookies.txt")

@app.route('/status', methods=['GET'])
def status():
    cookies_detectado = os.path.exists(COOKIES_PATH)
    return jsonify({
        "status": "Cortador de Vídeo Online!",
        "cookies_presente": cookies_detectado
    }), 200

@app.route('/cortar', methods=['POST'])
def cortar_video():
    data = request.json
    url_youtube = data.get("url")
    tempo_inicio = data.get("inicio")  # Formato "00:00:10"
    tempo_fim = data.get("fim")        # Formato "00:00:25"
    
    if not url_youtube or not tempo_inicio or not tempo_fim:
        return jsonify({"erro": "Parâmetros 'url', 'inicio' e 'fim' são obrigatórios."}), 400

    video_original_base = os.path.join(TEMP_DIR, "video_original")
    video_corte = os.path.join(TEMP_DIR, "corte_final.mp4")

    # Limpa arquivos de execuções anteriores
    for f in os.listdir(TEMP_DIR):
        if f.startswith("video_original") or f == "corte_final.mp4":
            try:
                os.remove(os.path.join(TEMP_DIR, f))
            except Exception:
                pass

    try:
        print(f"Baixando: {url_youtube}")
        
        # Configuração com User-Agent para simular navegador real
        ydl_opts = {
            'format': 'best', 
            'outtmpl': f"{video_original_base}.%(ext)s",
            'quiet': False,
            'nocheckcertificate': True,
            # Força cabeçalhos de um navegador real Chrome no Windows
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Sec-Fetch-Mode': 'navigate'
            }
        }

        if os.path.exists(COOKIES_PATH):
            print("🍪 Aplicando arquivo de cookies para download direto.")
            ydl_opts['cookiefile'] = COOKIES_PATH

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url_youtube])

        arquivos_baixados = glob.glob(f"{video_original_base}.*")
        if not arquivos_baixados:
            raise Exception("O download foi concluído, mas o arquivo de vídeo não foi encontrado no disco.")
        
        arquivo_baixado_real = arquivos_baixados[0]
        print(f"Arquivo baixado com sucesso em: {arquivo_baixado_real}")

        # 2. Executa o corte e converte/força a saída para MP4 compatível
        print(f"Cortando de {tempo_inicio} a {tempo_fim}")
        comando = [
            'ffmpeg', '-y',
            '-ss', tempo_inicio,
            '-to', tempo_fim,
            '-i', arquivo_baixado_real,
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-strict', 'experimental',
            video_corte
        ]
        subprocess.run(comando, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        return send_file(video_corte, mimetype='video/mp4', as_attachment=True, download_name='corte.mp4')

    except Exception as e:
        print(f"Erro no processamento: {str(e)}")
        return jsonify({"erro": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 5000)))
