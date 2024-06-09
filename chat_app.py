import tkinter as tk
from tkinter import scrolledtext, messagebox
from PIL import Image, ImageTk
import wikipedia
import os
import requests
from io import BytesIO
from pytube import YouTube
import threading
import logging
import ssl
import webbrowser

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat with our Companion")
        self.root.geometry("800x900")
        self.root.configure(bg='#2c3e50')

        # Define paths for saving images and videos
        self.image_directory = os.path.join(os.getcwd(), "images")
        self.video_directory = os.path.join(os.getcwd(), "videos")

        # Ensure directories exist
        os.makedirs(self.image_directory, exist_ok=True)
        os.makedirs(self.video_directory, exist_ok=True)

        self.heading_frame = tk.Frame(root, bg='#34495e', pady=10)
        self.heading_frame.pack(fill=tk.X)
        self.heading_label = tk.Label(self.heading_frame, text="Chat with our Companion", font=("Helvetica", 24, "bold"), fg='#ecf0f1', bg='#34495e')
        self.heading_label.pack()

        self.chat_display = scrolledtext.ScrolledText(root, wrap=tk.WORD, bg='#ecf0f1', fg='#2c3e50', font=("Helvetica", 12), padx=10, pady=10)
        self.chat_display.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.user_input_frame = tk.Frame(root, bg='#2c3e50')
        self.user_input_frame.pack(padx=10, pady=10, fill=tk.X)

        self.user_input = tk.Entry(self.user_input_frame, font=("Helvetica", 14), bg='#ecf0f1', fg='#2c3e50', relief=tk.GROOVE, bd=2)
        self.user_input.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.X, expand=True)
        self.user_input.bind("<Return>", self.send_message)

        self.send_button = tk.Button(self.user_input_frame, text="Send", command=self.send_message, font=("Helvetica", 14, "bold"), bg='#3498db', fg='#ecf0f1', activebackground='#2980b9', relief=tk.RAISED, bd=2)
        self.send_button.pack(side=tk.RIGHT, padx=10, pady=10)

        self.add_message("Bot", "Hello! Let's chat.\nYou can type 'bye', 'exit', or 'end' to stop the conversation.")

    def add_message(self, sender, message, is_hyperlink=False):
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, f"{sender}: ")
        if is_hyperlink:
            self.chat_display.insert(tk.END, message, "hyperlink")
            self.chat_display.tag_config("hyperlink", foreground="blue", underline=True)
            self.chat_display.tag_bind("hyperlink", "<Button-1>", lambda event: webbrowser.open(message))
        else:
            self.chat_display.insert(tk.END, message)
        self.chat_display.insert(tk.END, "\n\n")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.yview(tk.END)

    def send_message(self, event=None):
        user_message = self.user_input.get()
        if user_message.lower() in ['bye', 'exit', 'end']:
            self.add_message("Bot", "Goodbye! Have a great day!")
            self.root.after(2000, self.root.destroy)  # Close the window after 2 seconds
            return

        self.add_message("You", user_message)
        self.user_input.delete(0, tk.END)

        threading.Thread(target=self.process_user_message, args=(user_message,)).start()

    def process_user_message(self, message):
        response, image_path, video_path, video_url = self.get_bot_response(message)
        self.add_message("Bot", response)

        if image_path:
            self.show_image(image_path)
        if video_path:
            self.show_video(video_path)
        elif video_url:
            self.add_message("Bot:Here is a YouTube video link","{}".format(video_url),is_hyperlink=True)

    def get_bot_response(self, message):
        wiki_summary = self.fetch_wikipedia_summary(message)
        image_path = self.fetch_image(message)
        video_path, video_url = self.fetch_video(message)

        return wiki_summary, image_path, video_path, video_url

    def fetch_wikipedia_summary(self, message):
        try:
            return wikipedia.summary(message, sentences=5)
        except wikipedia.exceptions.DisambiguationError:
            return "It seems there are multiple possibilities. Can you be more specific?"
        except wikipedia.exceptions.PageError:
            return "Sorry, I couldn't find any information on that topic."
        except Exception as e:
            logging.error(f"Error fetching Wikipedia summary: {e}")
            return f"An error occurred: {e}"

    def fetch_image(self, message):
        try:
            unsplash_access_key = "q-5n88NIL_Fh3gOk0-lsJB2sTOnWyN3Kas3XGXIOC_Q"  # Replace with your Unsplash Access Key
            response = requests.get(f"https://api.unsplash.com/search/photos?query={message}&client_id={unsplash_access_key}")
            data = response.json()
            if data['results']:
                img_url = data['results'][0]['urls']['regular']
                img_response = requests.get(img_url)
                img = Image.open(BytesIO(img_response.content))
                image_path = os.path.join(self.image_directory, f"{message}.png")
                img.save(image_path)
                return image_path
            else:
                logging.info(f"No relevant image found for: {message}")
                return None
        except Exception as e:
            logging.error(f"Error fetching image: {e}")
            return None

    def fetch_video(self, message):
        youtube_api_key = "AIzaSyBEHKQ4RJxjI9aKANHhwpSIwXttL2DxcVI"  # Replace with your YouTube Data API key
        search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={message}&key={youtube_api_key}&type=video&maxResults=1"
        
        try:
            for attempt in range(3):  # Retry up to 3 times
                try:
                    response = requests.get(search_url)
                    data = response.json()
                    if data.get('items'):
                        video_id = data['items'][0]['id']['videoId']
                        video_url = f"https://www.youtube.com/watch?v={video_id}"
                        logging.info(f"Found video: {video_url}")

                        # Configure SSL context
                        ssl_context = ssl.create_default_context()

                        # Attempt to download the video using pytube
                        try:
                            yt = YouTube(video_url, ssl_context=ssl_context)
                            video_path = os.path.join(self.video_directory, f"{message}.mp4")
                            yt.streams.filter(progressive=True, file_extension='mp4').first().download(output_path=self.video_directory, filename=f"{message}.mp4")
                            logging.info(f"Video downloaded to: {video_path}")
                            return video_path, None
                        except Exception as e:
                            logging.error(f"Error downloading video: {e}")
                            return None, video_url
                    else:
                        logging.info(f"No relevant video found for: {message}")
                        return None, None
                except ssl.SSLError as e:
                    logging.error(f"SSL error: {e}. Retrying ({attempt + 1}/3)")
                    continue  # Retry the request
                except Exception as e:
                    logging.error(f"Error fetching video: {e}")
                    break  # Exit after other exceptions
            return None, None
        except Exception as e:
            logging.error(f"Error in fetch_video method: {e}")
            return None, None

    def show_image(self, image_path):
        if not os.path.exists(image_path):
            messagebox.showerror("Error", "Image not found!")
            return

        image_window = tk.Toplevel(self.root)
        image_window.title("Generated Image")
        img = ImageTk.PhotoImage(Image.open(image_path))
        panel = tk.Label(image_window, image=img)
        panel.image = img
        panel.pack()

    def show_video(self, video_path):
        if not os.path.exists(video_path):
            messagebox.showerror("Error", "Video not found!")
            return

        # Inform the user where the video is saved
        messagebox.showinfo("Video Generated", f"Video saved at: {video_path}")

if __name__ == "__main__":
    root = tk.Tk()
    app = ChatApp(root)
    root.mainloop()
