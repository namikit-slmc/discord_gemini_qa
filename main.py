# 必要なライブラリ
import discord
import google.generativeai as genai
import os
from flask import Flask
from threading import Thread

# --- (1) 各種キーを「環境変数」から取得 ---
# !! 重要 !! Renderの「Environment」タブでこれらの値を設定します
DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

# キーが設定されていない場合はエラーを出して終了
if not DISCORD_TOKEN or not GEMINI_API_KEY:
    print("エラー: 環境変数 DISCORD_BOT_TOKEN または GEMINI_API_KEY が設定されていません。", flush=True)
    exit()

# --- (2) Gemini APIの設定 ---
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- (3) Discord Botの設定 ---
intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
client = discord.Client(intents=intents)

# --- (4) RenderのためのWebサーバー設定 (Flask) ---
# これがRenderのヘルスチェックに応答し、スリープを防ぎます
app = Flask('')

@app.route('/')
def home():
    """UptimeRobotなどがアクセスする用"""
    return "Bot is alive!"

def run_web_server():
    """Webサーバーを別スレッドで実行する"""
    # RenderはPORT環境変数に自動でポート番号を割り当てます
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)

# --- (5) Discord Botのイベント ---
@client.event
async def on_ready():
    """Botが起動したときに呼ばれる"""
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
            async with message.channel.typing():
                response = await model.generate_content_async(question)
                answer = response.text
            
            await message.reply(answer)

        except Exception as e:
            print(f"Gemini APIエラー: {e}", flush=True)
            await message.reply("ごめんなさい、AIとの通信中にエラーが発生しました。")

# --- (6) BotとWebサーバーの同時起動 ---
if __name__ == "__main__":
    # Webサーバーを別スレッドで起動
    server_thread = Thread(target=run_web_server)
    server_thread.daemon = True  # メインスレッドが終了したら、こちらも終了
    server_thread.start()
    
    # Discord Botをメインスレッドで起動
    try:
        client.run(DISCORD_TOKEN)
    except discord.errors.LoginFailure:
        print("エラー: Discordトークンが不正です。Renderの環境変数を確認してください。")
    except Exception as e:
        print(f"Botの実行中に予期せぬエラーが発生しました: {e}")
