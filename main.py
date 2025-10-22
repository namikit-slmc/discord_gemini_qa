# 必要なライブラリ
import discord
import google.generativeai as genai
import os
from flask import Flask
from threading import Thread

# (変更点) Google APIの例外（ResourceExhaustedなど）をインポート
import google.api_core.exceptions as google_exceptions

# --- (1) 各種キーを「環境変数」から取得 ---
DISCORD_TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")

if not DISCORD_TOKEN or not GEMINI_API_KEY:
    print("エラー: 環境変数 DISCORD_BOT_TOKEN または GEMINI_API_KEY が設定されていません。")
    exit()

# --- (2) Gemini APIの設定 ---
genai.configure(api_key=GEMINI_API_KEY)
# (変更点) モデルを 'gemini-1.5-flash' に指定
model = genai.GenerativeModel('gemini-1.5-flash')

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
    print(f'{client.user} としてログインしました')

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
            
            await message.reply(answer)

        # --- (変更点) エラーハンドリングを強化 ---
        
        # (9-1) Gemini APIのレート制限 (混雑) エラーをキャッチ
        except google_exceptions.ResourceExhausted as e:
            print(f"Gemini API レート制限エラー: {e}")
            await message.reply(
                "ごめんなさい、今AIがとっても混み合っています 😥\n"
                "少し時間を置いてから、もう一度試してみてください。"
            )

        # (9-2) その他のエラー (APIキー間違い、安全設定ブロックなど)
        except Exception as e:
            print(f"!! 予期せぬエラー発生 !!: {e}")
            
            # 安全設定でブロックされた場合の簡易的な判定
            if "safety" in str(e).lower() or "blocked" in str(e).lower():
                await message.reply("ごめんなさい、その質問には安全上の理由でお答えできません。")
            else:
                await message.reply("ごめんなさい、AIとの通信中に予期せぬエラーが発生しました。")
        # --- (変更ここまで) ---

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
        print("エラー: Discordトークンが不正です。Renderの環境変数を確認してください。")
    except Exception as e:
        print(f"Botの実行中に予期せぬエラーが発生しました: {e}")
