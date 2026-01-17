import os
import numpy as np
import tensorflow as tf
from flask import Flask, render_template, request, jsonify, session
from google import genai
from google.genai import types
from dotenv import load_dotenv
from PIL import Image
import io

# .env ফাইল লোড করা
load_dotenv()

app = Flask(__name__)
app.secret_key = "agri_assistant_2025_tomato_r50_final"

# --- Gemini Configuration ---
# নিশ্চিত করুন আপনার .env ফাইলে GEMINI_API_KEY আছে
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
MODEL_ID = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")

SYSTEM_INSTRUCTION = (
    "You are 'Agri Bot', a professional agriculture expert in Bangladesh. "
    "Instructions: "
    "1. Always start every greeting with 'Assalamu Alaikum' (আসসালামু আলাইকুম). "
    "2. Always respond in Bengali (বাংলা). "
    "3. Provide expert advice on crops, pests, and soil in Bangladesh. "
    "4. Be polite and professional."
)

# --- TomatoNet-R50 Model Configuration ---
MODEL_PATH = 'TomatoNet_R50_best.h5'
tomato_model = None

def load_tomato_model():
    global tomato_model
    try:
        if os.path.exists(MODEL_PATH):
            tomato_model = tf.keras.models.load_model(MODEL_PATH)
            print("-" * 30)
            print("✅ TomatoNet-R50 Model Loaded Successfully!")
            print("-" * 30)
        else:
            print(f"❌ Error: {MODEL_PATH} not found in root directory.")
    except Exception as e:
        print(f"❌ Error loading model: {e}")

load_tomato_model()

# ৩টি ক্লাস (আপনার ট্রেনিং ডেটাসেট অনুযায়ী)
CLASS_NAMES = [
    'Tomato Yellow Leaf Curl Virus', 
    'Tomato Mosaic Virus', 
    'Healthy'
]

DISEASE_INFO = {
    'Tomato Yellow Leaf Curl Virus': {
        'name': "টমেটো ইয়েলো লিফ কার্ল ভাইরাস",
        'remedy': "এটি সাদা মাছি দ্বারা ছড়ায়। আক্রান্ত গাছ তুলে ধ্বংস করুন। সাদা মাছি দমনে ইমিডাক্লোপ্রিড গ্রুপের কীটনাশক ব্যবহার করুন।"
    },
    'Tomato Mosaic Virus': {
        'name': "টমেটো মোজাইক ভাইরাস",
        'remedy': "আক্রান্ত গাছ দ্রুত উপড়ে ফেলুন। চাষের সরঞ্জাম জীবাণুমুক্ত রাখুন এবং রোগমুক্ত বীজ ব্যবহার করুন।"
    },
    'Healthy': {
        'name': "সুস্থ টমেটো গাছ",
        'remedy': "আপনার গাছটি চমৎকার ও সুস্থ আছে। সঠিক পরিমাণ সেচ এবং সুষম সার প্রয়োগ অব্যহত রাখুন।"
    }
}

# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat')
def chat():
    if 'history' not in session:
        session['history'] = []
    return render_template('chat.html')

@app.route('/detect')
def detect_page():
    return render_template('detect.html')

# --- Gemini AI Chatbot Logic ---
@app.route('/get_response', methods=['POST'])
def get_response():
    user_message = request.json.get('message')
    if not user_message:
        return jsonify({"response": "বার্তা পাওয়া যায়নি"}), 400

    history = session.get('history', [])
    contents = []
    for item in history:
        contents.append(types.Content(role="user", parts=[types.Part.from_text(text=item['user'])]))
        contents.append(types.Content(role="model", parts=[types.Part.from_text(text=item['bot'])]))
    
    contents.append(types.Content(role="user", parts=[types.Part.from_text(text=user_message)]))

    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_INSTRUCTION,
                temperature=0.7
            )
        )
        bot_reply = response.text
        history.append({"user": user_message, "bot": bot_reply})
        session['history'] = history[-10:]
        session.modified = True
        return jsonify({"response": bot_reply})
    except Exception as e:
        print(f"Gemini Error: {e}")
        return jsonify({"response": "দুঃখিত, এআই সার্ভারে সংযোগ করা সম্ভব হচ্ছে না।"})

# --- Tomato Image Detection Logic (Strict Preprocessing) ---
@app.route('/predict_tomato', methods=['POST'])
def predict_tomato():
    if 'file' not in request.files:
        return jsonify({"error": "কোনো ছবি আপলোড করা হয়নি।"}), 400
    
    if tomato_model is None:
        return jsonify({"error": "ডিটেকশন মডেল লোড করা নেই।"}), 500
    
    file = request.files['file']
    try:
        # CMD Debugging Start
        print("\n" + "="*50)
        print("🔍 [DEBUG] New Detection Request Received")

        # ১. ইমেজ লোড এবং RGB কনভার্ট
        img = Image.open(io.BytesIO(file.read())).convert('RGB')
        
        # ২. ট্রেনিং স্ক্রিপ্ট অনুযায়ী ২২৪x২২৪ রিসাইজ
        img = img.resize((224, 224)) 
        
        # ৩. অ্যারেতে রূপান্তর এবং নরমালইজেশন (1/255)
        img_array = np.array(img).astype('float32') / 255.0
        img_array = np.expand_dims(img_array, axis=0)

        # ৪. প্রেডিকশন
        predictions = tomato_model.predict(img_array, verbose=0)
        class_idx = np.argmax(predictions[0])
        confidence = np.max(predictions[0]) * 100
        result_key = CLASS_NAMES[class_idx]
        
        # CMD Debugging Output
        print(f"📡 [CMD DEBUG] Detected: {result_key}")
        print(f"📡 [CMD DEBUG] Confidence: {confidence:.2f}%")
        print("="*50 + "\n")

        # ৫. ফলাফল সংগ্রহ
        info = DISEASE_INFO.get(result_key, {
            'name': "অজানা সমস্যা",
            'remedy': "নিকটস্থ কৃষি কর্মকর্তার পরামর্শ নিন।"
        })

        return jsonify({
            "class": info['name'],
            "remedy": info['remedy'],
            "confidence": f"{confidence:.2f}%"
        })

    except Exception as e:
        print(f"❌ [DEBUG ERROR] Detection Failed: {e}")
        return jsonify({"error": "ছবিটি বিশ্লেষণ করতে ত্রুটি হয়েছে।"}), 500

@app.route('/clear_chat', methods=['POST'])
def clear_chat():
    session.pop('history', None)
    return jsonify({"status": "success"})

if __name__ == '__main__':
    app.run(debug=True)