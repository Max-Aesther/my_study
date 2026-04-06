from fastapi import FastAPI, UploadFile, File, File
import os
import csv
import cv2
import numpy as np
import mediapipe as mp
from tensorflow.keras.layers import Dense, Input, GlobalAveragePooling1D
from tensorflow.keras.layers import MultiHeadAttention, LayerNormalization
from tensorflow.keras.models import Model
from tensorflow.keras.models import load_model
import tensorflow as tf
import logging
import whisper
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import uuid

# uvicorn app.main:app --reload

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # 허용할 오리진
    allow_credentials=True,
    allow_methods=["*"],          # GET, POST, OPTIONS 등 허용
    allow_headers=["*"],          # 모든 헤더 허용
)

logging.basicConfig(level=logging.INFO)

# 서버 실행 시 모델 로드
@app.on_event("startup")
def load_ai_model():
    
    global model, labels, speech_model
    
    if os.path.exists("sign_model.h5") and os.path.exists("labels.npy"):
        
        model = load_model("sign_model.h5")
        labels = np.load("labels.npy")

        logging.info("AI model loaded successfully.")
        
    else:
        logging.warning("AI model not found. Please ensure 'sign_model.h5' and 'labels.npy' exist.")
        
    speech_model = whisper.load_model("base")
    logging.info("Speech recognition model loaded successfully.")
        
# 배포 확인 api
@app.get("/")
async def root():
    return {"message": "Hello World"}

# 파일 업로드 확인 api
@app.post("/file/check")
async def predict(file: UploadFile = File(...)):
    contents = await file.read()
    return {"filename": file.filename, "content_type": file.content_type}

mp_hands = mp.solutions.hands
mp_pose = mp.solutions.pose

hands = mp_hands.Hands(static_image_mode=False)
pose = mp_pose.Pose()

# keypoint 생성 함수
def extract_keypoints(frame):
    
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
    hand_results = hands.process(frame_rgb)
    pose_results = pose.process(frame_rgb)
    
    keypoints = []
    
    # pose
    if pose_results.pose_landmarks:
        for lm in pose_results.pose_landmarks.landmark:
            keypoints.extend([lm.x, lm.y, lm.z])
    else:
        keypoints.extend([0] * 99)  
        
    # hands
    
    left_hand = [0] * 63
    right_hand = [0] * 63
    
    if hand_results.multi_hand_landmarks:
        for hand_landmarks, handedness in zip(hand_results.multi_hand_landmarks, hand_results.multi_handedness):
            
            hand_kp = []
            
            for lm in hand_landmarks.landmark:
                hand_kp.extend([lm.x, lm.y, lm.z])
                
            label = handedness.classification[0].label
            
            if label == "Left":
                left_hand = hand_kp
            elif label == "Right":
                right_hand = hand_kp
    
    keypoints.extend(left_hand)
    keypoints.extend(right_hand)
    
    return keypoints

# 활성 구간 추출 함수
def extract_active_frames(frames, threshold=0.01, min_length=30):
    """
    손 keypoint 움직임이 있는 구간만 추출
    frames: list of keypoints (각 225차원)
    """
    # 손 keypoint만 추출 (pose 99개 이후, 126개가 손)
    hand_kps = np.array(frames)[:, 99:]  # shape: (N, 126)
    
    # 프레임 간 움직임 계산
    motion = np.sum(np.abs(np.diff(hand_kps, axis=0)), axis=1)  # shape: (N-1,)
    
    # 움직임이 threshold 이상인 구간 탐지
    active = motion > threshold
    
    # 연속된 활성 구간 찾기
    active_indices = np.where(active)[0]
    
    if len(active_indices) == 0:
        return None
    
    start = max(0, active_indices[0] - 5)        # 약간 여유 포함
    end = min(len(frames), active_indices[-1] + 5)
    
    active_frames = frames[start:end + 1]
    
    if len(active_frames) < min_length:
        return None
    
    return active_frames
        
# segmentaion 함수(문장 구분)
def split_sements_with_pause(frames, motion_threshold=0.01, pause_threshold=0.8, fps=30):
    
    handkps = np.array(frames)[:, 99:]
    motion = np.sum(np.abs(np.diff(handkps, axis=0)), axis=1)
    
    segments = []
    start = None
    pause_count = 0
    
    for i, m in enumerate(motion):
        
        if m > motion_threshold:
            if start is None:
                start = i
            pause_count = 0
        else:
            if start is not None:
                pause_count += 1
                if pause_count >= pause_threshold:  # 0.8초 이상 멈춤
                    segments.append((start, i))
                    start = None
                    pause_count = 0
    
    if start is not None:
        segments.append((start, len(frames) - 1))
    
    return segments

# segmentaion 함수(단어 구분 및 중복 제거)
def predict_words_in_segment(segment, model, labels, window=30, stride=3, threshold=0.5):
    
    predictions = []
    
    for start in range(0, len(segment) - window + 1, stride):
        
        seq = np.array(segment[start:start+window])
        seq = np.expand_dims(seq, axis=0)
        
        pred = model.predict(seq, verbose=0)[0]
        idx = np.argmax(pred)
        conf = pred[idx]
        
        if conf > threshold:
            predictions.append(idx)
        else:
            predictions.append(-1)  # 불확실한 예측은 -1로 표시
            
    words = []
    prev = None
    
    for idx in predictions:
        if idx == -1:
            continue
        if idx != prev:
            words.append(labels[idx])
            prev = idx
    
    return words
            
    

# 학습용 dataset 생성 api(직접 수동으로 파일을 보내는 경우)
@app.post("/create/dataset")
async def create_dataset(file: UploadFile = File(...)):
    
    label = "find"
    dataset_dir = os.path.join("dataset", label)
    os.makedirs(dataset_dir, exist_ok=True)
    
    video_path = f"temp_{uuid.uuid4().hex}_{file.filename}"
    try:
        with open(video_path, "wb") as f:
            f.write(await file.read())
                
        cap = cv2.VideoCapture(video_path)
        frames = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            kp = extract_keypoints(frame)
            frames.append(kp)
        
        cap.release()
        os.remove(video_path)
        
        frames = np.array(frames)
        
        # 수어 활성 구간만 추출
        active_frames = extract_active_frames(frames)
        
        if active_frames is None:
            return {"status": "error", "message": "수어 동작 구간을 찾을 수 없습니다"}
        
        print(f"전체 프레임: {len(frames)}, 활성 구간: {len(active_frames)}")
        
        window = 30
        stride = 5
        
        if len(active_frames) < window:
            return {"status": "error", "message": "활성 구간이 너무 짧습니다"}
        
        existing = len(os.listdir(dataset_dir))
        csv_index = existing
        
        for start in range(0, len(active_frames) - window + 1, stride):
            seq = active_frames[start:start + window]
            csv_path = os.path.join(dataset_dir, f"{label}_{csv_index}.csv")
            
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                for row in seq:
                    writer.writerow(row)
            
            csv_index += 1
        
        return {
            "status": "created",
            "label": label,
            "total_frames": len(frames),
            "active_frames": len(active_frames),
            "csv_files": csv_index
        }  
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)

# 학습용 dataset 생성 함수(자동으로 폴더에서 파일을 읽는 경우)
def create_dataset_from_folder():
    
    folder = r"C:\Users\noua0\OneDrive\Desktop\calling_dataset"
    
    for file in os.listdir(folder):

        if not file.endswith(".mp4"):
            continue
        
        video_path = os.path.join(folder, file)
        
        # 파일 이름을 라벨로 사용
        label = os.path.splitext(file)[0]
        
        dataset_dir = os.path.join("dataset", label)
        os.makedirs(dataset_dir, exist_ok=True)
        
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            logging.warning(f"비디오 파일을 열 수 없습니다: {file}")
            continue
        
        frames = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            kp = extract_keypoints(frame)
            frames.append(kp)
            
        cap.release()
        
        frames = np.array(frames)
        
        active_frames = extract_active_frames(frames)
        
        if active_frames is None:
            logging.warning(f"활성 구간을 찾을 수 없습니다: {file}")
            continue
        
        window = 30
        stride = 5
        
        if len(active_frames) < window:
            logging.warning(f"활성 구간이 너무 짧습니다: {file}")
            continue
        
        existing = len(os.listdir(dataset_dir))
        csv_index = existing
        
        for start in range(0, len(active_frames) - window + 1, stride):
            
            seq = active_frames[start:start + window]
            csv_path = os.path.join(dataset_dir, f"{label}_{csv_index}.csv")
            
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                
                for row in seq:
                    writer.writerow(row)
            
            csv_index += 1

# 학습용 dataset 자동 생성 api(폴더에서 자동으로 파일을 읽는 경우)
@app.get("/create/dataset/auto")
async def create_dataset_auto():
    try:
        create_dataset_from_folder()
        return {"status": "created"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# 학습용 dataset 로딩 함수(모델 학습 데이터 준비)
def load_dataset():
    
    x = []
    y = []
    
    dataset_path = "dataset"
    labels = os.listdir(dataset_path)
    
    label_map = {label:i for i, label in enumerate(labels)}
    
    for label in labels:
        
        folder = os.path.join(dataset_path, label)
        
        for file in os.listdir(folder):
            
            if file.endswith(".csv"):
                
                path = os.path.join(folder, file)
                
                data = np.loadtxt(path, delimiter=",")
                
                x.append(data)
                y.append(label_map[label])
    
    return np.array(x), np.array(y), labels

# 모델 정의 함수(생성, 학습)
def train_model():
    
    X, y, labels = load_dataset()
    
    num_classes = len(labels)
    
    y = tf.keras.utils.to_categorical(y, num_classes)
    
    inputs = Input(shape=(30, 225))
    
    x = MultiHeadAttention(num_heads=4, key_dim=64)(inputs, inputs)
    x = LayerNormalization()(x)
    
    x = GlobalAveragePooling1D()(x)
    
    outputs = Dense(num_classes, activation="softmax")(x)
    
    model = Model(inputs, outputs)
    
    model.compile(
        optimizer="adam",
        loss="categorical_crossentropy",
        metrics=["accuracy"]
    )
    
    model.fit(X, y, epochs=50)
    
    model.save("sign_model.h5")
               
    np.save("labels.npy", labels)
    
@app.get("/train")
async def train():
    try:
        train_model()
        return {"status": "model trained"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
@app.post("/predict/word")
async def predict_test(file: UploadFile = File(...)):
    try:
        video_path = f"temp_{uuid.uuid4().hex}_{file.filename}"
        with open(video_path, "wb") as f:
            f.write(await file.read())
            
        cap = cv2.VideoCapture(video_path)
        frames = []
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            kp = extract_keypoints(frame)
            frames.append(kp)
        
        cap.release()
        os.remove(video_path)
        
        # 예측도 활성 구간만 사용
        active_frames = extract_active_frames(np.array(frames))
        
        if active_frames is None or len(active_frames) < 30:
            return {"status": "error", "message": "수어 동작 구간을 찾을 수 없습니다"}
        
        # 슬라이딩 윈도우로 여러 구간 예측 후 평균
        sequences = []
        for start in range(0, len(active_frames) - 30 + 1, 5):
            seq = np.array(active_frames[start:start + 30])
            sequences.append(seq)
        
        sequences = np.array(sequences)
        preds = model.predict(sequences)
        avg_pred = preds.mean(axis=0)
        
        pred_label = labels[np.argmax(avg_pred)]
        confidence = float(avg_pred[np.argmax(avg_pred)])
        
        confidence = round(confidence * 100)
        
        if confidence < 0.6:
            return {"status": "uncertain", "prediction": pred_label, "confidence": confidence}
        
        return {"status": "success", "prediction": pred_label, "confidence": confidence}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}    
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
    
        
def extract_frames_from_video(video_path):
    cap = cv2.VideoCapture(video_path)
    frames = []
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        kp = extract_keypoints(frame)
        frames.append(kp)
    
    cap.release()
    
    return np.array(frames)
        
# 문장 예측 함수
def predict_sentence_segment(frames, model, labels):
    
    segments = split_sements_with_pause(frames)
    
    sentences = []
    
    for start, end in segments:
        segment = frames[start:end]
        
        if len(segment) < 30:
            continue
        
        words = predict_words_in_segment(segment, model, labels)
        
        if len(words) > 0:
            sentence = " ".join(words)
            sentences.append(sentence)
    
    return sentences

# 문장 예측 api
@app.post("/predict/sentence")
async def predict_sentence(file: UploadFile = File(...)):
        
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name    
        
        frames = extract_frames_from_video(tmp_path)
    
        if len(frames) < 30:
            return {"status": "error", "message": "영상이 너무 짧습니다"}
    
        words = predict_sentence_segment(frames, model, labels)
        
        setence = " ".join(words)
    
        return {"status": "success", "words": words, "sentence": setence}
                
    except Exception as e:
        return {"status": "error", "message": str(e)}
    
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        
    
# 음성 텍스트 반환 함수
def extract_speech_list(video_path):
    result = speech_model.transcribe(video_path)
    
    speech_list = []
    
    for seg in result["segments"]:
        speech_list.append(seg["text"].strip())
    
    return speech_list

# 음성 텍스트 변환 api
@app.post("/audio")
async def audio(file: UploadFile = File(...)):
    try:
        video_path = f"temp_{uuid.uuid4().hex}_{file.filename}"
        
        with open(video_path, "wb") as f:
            f.write(await file.read())
        
        speech_list = extract_speech_list(video_path)
        
        os.remove(video_path)
        
        return {"status": "success", "speech": speech_list}
    
    except Exception as e:
        return {"status": "error", "message": str(e)}
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
