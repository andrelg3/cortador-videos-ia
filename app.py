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
    # Verifica se o arquivo de cookies realmente existe na pasta para facilitar o debug
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

    # Usamos uma base genérica para o arquivo baixado
    video_original_base = os.path.join(TEMP_DIR, "video_original")
    video_corte = os.path.join(TEMP_DIR, "corte_final.mp4")

    # Limpa arquivos de execuções anteriores no diretório temporário
    for f in os.listdir(TEMP_DIR):
        if f.startswith("video_original") or f == "corte_final.mp4":
            try:
                os.remove(os.path.join(TEMP_DIR, f))
            except Exception:
                pass

    try:
        print(f"Baixando: {url_youtube}")
        
        # Configuração flexível: baixa o melhor formato disponível (mp4 se possível, ou qualquer outro)
        ydl_opts = {
            'format': 'best', 
            'outtmpl': f"{video_original_base}.%(ext)s",
            'quiet': False,  # Desativamos o quiet para podermos ver o log se der erro
            'nocheckcertificate': True,
        }

        if os.path.exists(COOKIES_PATH):
            print("🍪 Aplicando arquivo de cookies para download direto.")
            ydl_opts['cookiefile'] = COOKIES_PATH
        else:
            print("⚠️ ATENÇÃO: youtube-cookies.txt NÃO encontrado na raiz!")

        # Realiza o download direto (método que funcionou contra o bot check)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url_youtube])

        # Como o formato 'best' pode baixar .mp4, .mkv, .webm, buscamos o arquivo real gerado
        arquivos_baixados = glob.glob(f"{video_original_base}.*")
        if not arquivos_baixados:
            raise Exception("O download foi concluído, mas o arquivo de vídeo não foi encontrado no disco.")
        
        arquivo_baixado_real = arquivos_baixados[0]
        print(f"Arquivo baixado com sucesso em: {arquivo_baixado_real}")

        # 2. Executa o corte e força a saída a ser convertida em um MP4 perfeito
        print(f"Cortando de {tempo_inicio} a {tempo_fim}")
        comando = [
            'ffmpeg', '-y',
            '-ss', tempo_inicio,
            '-to', tempo_fim,
            '-i', arquivo_baixado_real,
            '-c:v', 'libx264',   # Garante a conversão de vídeo para H.264
            '-c:a', 'aac',       # Garante a conversão de áudio para AAC
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
