# 必要なライブラリ
import discord
import google.generativeai as genai
import os
from flask import Flask
from threading import Thread

# --- (1) 各種キーを「環境変数」から取得 ---
DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not DISCORD_TOKEN or not GEMINI_API_KEY:
    # (変更点) flush=True を追加
    print("エラー: 環境変数 DISCORD_BOT_TOKEN または GEMINI_API_KEY が設定されていません。", flush=True)
    exit()

# --- (2) Gemini APIの設定 ---
genai.configure(api_key=GEMINI_API_KEY)
# モデルを 'gemini-2.5-flash' に指定
model = genai.GenerativeModel('gemini-2.5-flash')

# --- (3) Discord Botの設定 ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

# --- (4) RenderのためのWebサーバー設定 (Flask) ---
app = Flask('')

@app.route('/')
def home():
    """UptimeRobotなどがアクセスする用"""
    return "Bot is alive!"

def run_web_server():
    """Webサーバーを別スレッドで実行する"""
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- (5) Discord Botのイベント ---
@client.event
async def on_ready():
    """Botが起動したときに呼ばれる"""
    # (変更点) flush=True を追加
    print(f'{client.user} としてログインしました', flush=True)

@client.event
async def on_message(message):
    """Discordで誰かがメッセージを投稿するたびに呼ばれる"""
    
    if message.author == client.user:
        return

    if client.user.mentioned_in(message):
        
        question = message.content.replace(f'<@{client.user.id}>', '').strip()

        if not question:
            await message.reply("メンションの後に、質問内容を続けてくださいね！")
            return

        try:
            # 「考え中...」と表示
            async with message.channel.typing():
                response = await model.generate_content_async(question)
                answer = response.text

            # --- 回答の長さをチェックして分割送信 ---
            if len(answer) <= 2000:
                # 2000文字以下なら、そのままリプライ
                await message.reply(answer)
            else:
                # 2000文字を超える場合
                # (変更点) flush=True を追加
                print(f"回答が2000文字を超えました (長さ: {len(answer)})。分割して送信します。", flush=True)
                
                # 最初の2000文字をリプライとして送信
                first_chunk = answer[:2000]
                await message.reply(first_chunk)
                
                # 残りの部分を2000文字ごとに区切って送信
                remaining_answer = answer[2000:]
                for i in range(0, len(remaining_answer), 2000):
                    chunk = remaining_answer[i:i+2000]
                    # 2回目以降はリプライではなく、チャンネルにそのまま送信
                    await message.channel.send(chunk)
            # --- (変更ここまで) ---

        except Exception as e:
            # シンプルなエラー処理
            # (変更点) flush=True を追加
            print(f"!! 予期せぬエラー発生 !!: {e}", flush=True)
            await message.reply("ごめんなさい、AIとの通信中にエラーが発生しました。")

# --- (6) BotとWebサーバーの同時起動 ---
if __name__ == "__main__":
    # Webサーバーを別スレッドで起動
    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True
    server_thread.start()
    
    # Discord Botをメインスレッドで起動
    try:
        client.run(DISCORD_TOKEN)
    except discord.errors.LoginFailure:
        # (変更点) flush=True を追加
        print("エラー: Discordトークンが不正です。Renderの環境変数を確認してください。", flush=True)
    except Exception as e:
        # (変更点) flush=True を追加
        print(f"Botの実行中に予期せぬエラーが発生しました: {e}", flush=True)