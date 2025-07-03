import os
import re
import streamlit as st
from PIL import Image
import pytesseract
import spacy

# Load spaCy model
nlp = spacy.load("en_core_web_sm")

# Folder where Telegram images are downloaded
downloads_folder = "downloads"
os.makedirs(downloads_folder, exist_ok=True)

# OCR + text extraction
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

# spaCy-based summary: extract top 5 longest sentences
def summarize_with_spacy(text, max_sentences=5):
    doc = nlp(text)
    sentences = sorted([sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 30],
                       key=lambda x: -len(x))
    return " ".join(sentences[:max_sentences])

# Streamlit UI
st.title("🧠 Telegram Image OCR + spaCy Summarizer")

if st.button("Run OCR and Summarize"):
    ocr_results = extract_text_from_images()
    if not ocr_results:
        st.warning("No images found in the downloads folder.")
    else:
        full_text = " ".join([text for _, text in ocr_results])
        summary = summarize_with_spacy(full_text)

        st.subheader("📄 OCR Extracted Text")
        for filename, text in ocr_results:
            st.markdown(f"**{filename}**\n\n{text}\n\n---")

        st.subheader("🔍 Summary (spaCy)")
        st.write(summary)

        # Optional save
        with open("summary.txt", "w", encoding="utf-8") as f:
            f.write(summary)
