import os
import re
import asyncio
import streamlit as st
from PIL import Image
import pytesseract
import spacy
import requests
from telethon.sync import TelegramClient

# ========== CONFIG (from secrets) ==========
api_id = st.secrets["telegram"]["api_id"]
api_hash = st.secrets["telegram"]["api_hash"]
group_name = st.secrets["telegram"]["group_name"]
downloads_folder = "downloads"
slack_webhook_url = st.secrets["slack"]["webhook_url"]

# ========== INIT ==========
os.makedirs(downloads_folder, exist_ok=True)
nlp = spacy.load("en_core_web_sm")

# ========== FETCH FROM TELEGRAM ==========
async def fetch_images():
    client = TelegramClient('session_name', api_id, api_hash)
    await client.start()
    entity = await client.get_entity(group_name)
    messages = await client.get_messages(entity, limit=30)

    for msg in messages:
        if msg.photo:
            filename = f"{msg.date.strftime('%Y-%m-%d_%H-%M-%S')}.jpg"
            path = os.path.join(downloads_folder, filename)
            if not os.path.exists(path):
                try:
                    await msg.download_media(file=path)
                    print(f"✅ Downloaded: {filename}")
                except Exception as e:
                    print(f"❌ Error: {e}")
    await client.disconnect()

def fetch_telegram_images():
    if not asyncio.get_event_loop().is_running():
        asyncio.run(fetch_images())

# ========== OCR ==========
def extract_text_from_images(folder=downloads_folder):
    texts = []
    for img_file in os.listdir(folder):
        if img_file.lower().endswith(('jpg', 'jpeg', 'png')):
            path = os.path.join(folder, img_file)
            try:
                img = Image.open(path)
                raw_text = pytesseract.image_to_string(img)
                cleaned = re.sub(r'\s+', ' ', raw_text).strip()
                texts.append((img_file, cleaned))
            except Exception as e:
                st.error(f"Failed to process {img_file}: {e}")
    return texts

# ========== spaCy Summary ==========
def summarize_with_spacy(text, max_sentences=5):
    doc = nlp(text)
    sentences = sorted([sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 30],
                       key=lambda x: -len(x))
    return "\n".join(["• " + s for s in sentences[:max_sentences]])

# ========== Slack ==========
def send_summary_to_slack(summary_text):
    payload = {
        "text": f"""📄 *Auto-Summary from Telegram OCR:*

{summary_text}
"""
    }
    response = requests.post(slack_webhook_url, json=payload)
    return response.status_code == 200

# ========== Streamlit UI ==========
st.title("📩 Telegram OCR Summarizer + Slack + GPT Prompt")

# === Step 1: Fetch Telegram Images ===
if st.button("📥 1. Fetch Telegram Images", key="fetch_btn"):
    fetch_telegram_images()
    st.success("✅ Images fetched from Telegram group.")

# === Step 2: OCR + Summarize ===
if st.button("🔎 2. Run OCR and Summarize", key="ocr_btn"):
    ocr_results = extract_text_from_images()
    if not ocr_results:
        st.warning("⚠️ No valid images found in the downloads folder.")
    else:
        full_text = " ".join(text for _, text in ocr_results)
        summary = summarize_with_spacy(full_text)

        st.subheader("🖼️ OCR Extracted Text")
        for filename, text in ocr_results:
            st.markdown(f"**{filename}**\n\n{text}\n\n---")

        st.subheader("🧠 Summary (spaCy)")
        st.markdown(summary)

        with open("summary.txt", "w", encoding="utf-8") as f:
            f.write(summary)

        if st.button("🚀 Send to Slack", key="slack_btn"):
            if send_summary_to_slack(summary):
                st.success("✅ Summary sent to Slack!")
            else:
                st.error("❌ Failed to send summary to Slack.")

        st.subheader("🤖 GPT Prompt for ChatGPT")
        prompt_text = (
            "Summarize the key stock-related insights from the following text.\n"
            "Group the points by stock name (like TATASTEEL, HDFC, etc.) and write each insight as a short bullet point:\n\n"
            f"{full_text}"
        )
        st.text_area("📋 Copy-paste this prompt into ChatGPT", prompt_text, height=300)
