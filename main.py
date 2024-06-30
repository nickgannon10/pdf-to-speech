import os
import re
import logging
from pathlib import Path
from moviepy.editor import concatenate_audioclips, AudioFileClip
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Convert Markdown to plain text
def markdown_to_plain_text(markdown_text):
    logging.info("Converting markdown to plain text")
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', markdown_text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'\_\_([^_]+)\_\_', r'\1', text)
    text = re.sub(r'\_([^_]+)\_', r'\1', text)
    text = re.sub(r'#+\s?', '', text)
    text = re.sub(r'-\s?', '', text)
    text = re.sub(r'>\s?', '', text)
    logging.info("Finished converting markdown to plain text")
    return text

# Chunk the text into smaller segments
def split_text(text, max_chunk_size=4000):
    logging.info("Splitting text into chunks")
    chunks = []
    current_chunk = ""
    for sentence in text.split('.'):
        sentence = sentence.strip()
        if not sentence:
            continue
        if len(current_chunk) + len(sentence) + 1 <= max_chunk_size:
            current_chunk += sentence + "."
        else:
            chunks.append(current_chunk)
            current_chunk = sentence + "."
    if current_chunk:
        chunks.append(current_chunk)
    logging.info(f"Text split into {len(chunks)} chunks")
    return chunks

# Text-to-Speech conversion
def text_to_speech(input_text, output_file, model="tts-1-hd", voice="nova"):
    logging.info(f"Converting text to speech for {output_file}")
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    response = client.audio.speech.create(
        model=model,
        voice=voice,
        input=input_text
    )
    
    with open(output_file, 'wb') as f:
        for chunk in response.iter_bytes():
            f.write(chunk)
    
    logging.info(f"Audio saved to {output_file}")

# Convert text chunks to audio files
def convert_chunks_to_audio(chunks, output_folder):
    logging.info(f"Converting chunks to audio files in folder: {output_folder}")
    audio_files = []
    for i, chunk in enumerate(chunks):
        output_file = os.path.join(output_folder, f"chunk_{i+1}.mp3")
        text_to_speech(chunk, output_file)
        audio_files.append(output_file)
    logging.info(f"Converted {len(audio_files)} chunks to audio files")
    return audio_files

# Combine individual audio clips into a single file
def combine_audio_with_moviepy(folder_path, output_file):
    logging.info(f"Combining audio files in folder: {folder_path} into {output_file}")
    audio_clips = []
    for file_name in sorted(os.listdir(folder_path)):
        if file_name.endswith('.mp3'):
            file_path = os.path.join(folder_path, file_name)
            logging.info(f"Processing file: {file_path}")
            try:
                clip = AudioFileClip(file_path)
                audio_clips.append(clip)
            except Exception as e:
                logging.error(f"Error processing file {file_path}: {e}")
    if audio_clips:
        final_clip = concatenate_audioclips(audio_clips)
        final_clip.write_audiofile(output_file)
        logging.info(f"Combined audio saved to {output_file}")
    else:
        logging.warning("No audio clips to combine.")

# Process markdown files in the blogs directory
def process_markdown_files(directory, output_folder="chunks"):
    if os.path.exists(output_folder):
        for file in os.listdir(output_folder):
            os.remove(os.path.join(output_folder, file))
    else:
        os.makedirs(output_folder)

    for markdown_file in os.listdir(directory):
        if markdown_file.endswith('.md'):
            logging.info(f"Processing markdown file: {markdown_file}")
            try:
                with open(os.path.join(directory, markdown_file), 'r', encoding='utf-8') as file:
                    markdown_text = file.read()

                plain_text = markdown_to_plain_text(markdown_text)
                chunks = split_text(plain_text)
                audio_files = convert_chunks_to_audio(chunks, output_folder)

                output_audio_file = os.path.join(directory, f"{os.path.splitext(markdown_file)[0]}.mp3")
                combine_audio_with_moviepy(output_folder, output_audio_file)
                logging.info(f"Processed {markdown_file} into {output_audio_file}")
            except Exception as e:
                logging.error(f"Error processing {markdown_file}: {str(e)}")

# Main execution
if __name__ == "__main__":
    process_markdown_files('blogs')