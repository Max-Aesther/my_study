# from fastapi import FastAPI, UploadFile, File, HTTPException
# import os
# import csv
# import cv2
# import numpy as np
# import mediapipe as mp
# from tensorflow.keras.layers import Dense, Input, GlobalAveragePooling1D
# from tensorflow.keras.layers import MultiHeadAttention, LayerNormalization
# from tensorflow.keras.models import Model
# from tensorflow.keras.models import load_model
# import tensorflow as tf
# import logging
# import whisper
# from fastapi.middleware.cors import CORSMiddleware
# import tempfile
# import uuid

# # uvicorn app.main:app --reload

# app = FastAPI()

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["*"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# logging.basicConfig(level=logging.INFO)

# # 전역 모델 변수 초기화 (로드 전 None으로 명시)
# model = None
# labels = None
# speech_model = None

# # 서버 실행 시 모델 로드
# @app.on_event("startup")
# def load_ai_model():
    
#     global model, labels, speech_model
    
#     if os.path.exists("sign_model.h5") and os.path.exists("labels.npy"):
#         model = load_model("sign_model.h5")
#         labels = np.load("labels.npy")
#         logging.info("AI model loaded successfully.")
#     else:
#         logging.warning("AI model not found. Please ensure 'sign_model.h5' and 'labels.npy' exist.")
        
#     speech_model = whisper.load_model("base")
#     logging.info("Speech recognition model loaded successfully.")

# # 모델 로드 여부 확인 헬퍼
# def check_model_loaded():
#     if model is None or labels is None:
#         raise HTTPException(status_code=503, detail="AI 모델이 아직 로드되지 않았습니다.")

# # 배포 확인 api
# @app.get("/")
# async def root():
#     return {"message": "Hello World"}

# # 파일 업로드 확인 api
# @app.post("/file/check")
# async def predict(file: UploadFile = File(...)):
#     contents = await file.read()
#     return {"filename": file.filename, "content_type": file.content_type}

# mp_hands = mp.solutions.hands
# mp_pose = mp.solutions.pose

# hands = mp_hands.Hands(static_image_mode=False)
# pose = mp_pose.Pose()

# # keypoint 생성 함수
# def extract_keypoints(frame):
    
#     frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    
#     hand_results = hands.process(frame_rgb)
#     pose_results = pose.process(frame_rgb)
    
#     keypoints = []
    
#     # pose
#     if pose_results.pose_landmarks:
#         for lm in pose_results.pose_landmarks.landmark:
#             keypoints.extend([lm.x, lm.y, lm.z])
#     else:
#         keypoints.extend([0] * 99)  
        
#     # hands
#     left_hand = [0] * 63
#     right_hand = [0] * 63
    
#     if hand_results.multi_hand_landmarks:
#         for hand_landmarks, handedness in zip(hand_results.multi_hand_landmarks, hand_results.multi_handedness):
            
#             hand_kp = []
            
#             for lm in hand_landmarks.landmark:
#                 hand_kp.extend([lm.x, lm.y, lm.z])
                
#             label = handedness.classification[0].label
            
#             if label == "Left":
#                 left_hand = hand_kp
#             elif label == "Right":
#                 right_hand = hand_kp
    
#     keypoints.extend(left_hand)
#     keypoints.extend(right_hand)
    
#     return keypoints

# # 활성 구간 추출 함수
# def extract_active_frames(frames, threshold=0.01, min_length=30):
#     """
#     손 keypoint 움직임이 있는 구간만 추출
#     frames: list of keypoints (각 225차원)
#     """
#     hand_kps = np.array(frames)[:, 99:]  # shape: (N, 126)
    
#     motion = np.sum(np.abs(np.diff(hand_kps, axis=0)), axis=1)  # shape: (N-1,)
    
#     active = motion > threshold
    
#     active_indices = np.where(active)[0]
    
#     if len(active_indices) == 0:
#         return None
    
#     start = max(0, active_indices[0] - 5)
#     end = min(len(frames), active_indices[-1] + 5)
    
#     active_frames = frames[start:end + 1]
    
#     if len(active_frames) < min_length:
#         return None
    
#     return active_frames
        
# # segmentation 함수(문장 구분)
# # pause_threshold: 몇 프레임 이상 멈추면 단어 경계로 볼지 (FPS 고려해서 조정 필요, 기본 24fps 기준 약 0.8초 = 19프레임)
# def split_segments_with_pause(frames, motion_threshold=0.01, pause_threshold=19):
    
#     handkps = np.array(frames)[:, 99:]
#     motion = np.sum(np.abs(np.diff(handkps, axis=0)), axis=1)
    
#     segments = []
#     start = None
#     pause_count = 0
    
#     for i, m in enumerate(motion):
        
#         if m > motion_threshold:
#             if start is None:
#                 start = i
#             pause_count = 0
#         else:
#             if start is not None:
#                 pause_count += 1
#                 if pause_count >= pause_threshold:
#                     segments.append((start, i))
#                     start = None
#                     pause_count = 0
    
#     if start is not None:
#         segments.append((start, len(frames) - 1))
    
#     return segments

# # segmentation 함수(단어 구분 및 중복 제거)
# def predict_words_in_segment(segment, mdl, lbls, window=30, stride=5, threshold=0.7):
    
#     predictions = []
    
#     for start in range(0, len(segment) - window + 1, stride):
        
#         seq = np.array(segment[start:start + window])
#         seq = np.expand_dims(seq, axis=0)  # ✅ npx -> np 오타 수정
        
#         pred = mdl.predict(seq, verbose=0)[0]
#         idx = np.argmax(pred)
#         conf = pred[idx]
        
#         if conf > threshold:
#             predictions.append(idx)
#         else:
#             predictions.append(-1)
            
#     words = []
#     prev = None
    
#     for idx in predictions:
#         if idx == -1:
#             continue
#         if idx != prev:
#             words.append(lbls[idx])
#             prev = idx
    
#     return words
            
# # 학습용 dataset 생성 api(직접 수동으로 파일을 보내는 경우)
# @app.post("/create/dataset")
# async def create_dataset(file: UploadFile = File(...)):
    
#     label = "change"
#     dataset_dir = os.path.join("dataset", label)
#     os.makedirs(dataset_dir, exist_ok=True)
    
#     # ✅ uuid로 임시파일명 충돌 방지
#     video_path = f"temp_{uuid.uuid4().hex}_{file.filename}"
#     try:
#         with open(video_path, "wb") as f:
#             f.write(await file.read())
                
#         cap = cv2.VideoCapture(video_path)
#         frames = []
        
#         while cap.isOpened():
#             ret, frame = cap.read()
#             if not ret:
#                 break
#             kp = extract_keypoints(frame)
#             frames.append(kp)
        
#         cap.release()
        
#         frames = np.array(frames)
        
#         active_frames = extract_active_frames(frames)
        
#         if active_frames is None:
#             return {"status": "error", "message": "수어 동작 구간을 찾을 수 없습니다"}
        
#         print(f"전체 프레임: {len(frames)}, 활성 구간: {len(active_frames)}")
        
#         window = 30
#         stride = 5
        
#         if len(active_frames) < window:
#             return {"status": "error", "message": "활성 구간이 너무 짧습니다"}
        
#         existing = len(os.listdir(dataset_dir))
#         csv_index = existing
        
#         for start in range(0, len(active_frames) - window + 1, stride):
#             seq = active_frames[start:start + window]
#             csv_path = os.path.join(dataset_dir, f"{label}_{csv_index}.csv")
            
#             with open(csv_path, "w", newline="") as f:
#                 writer = csv.writer(f)
#                 for row in seq:
#                     writer.writerow(row)
            
#             csv_index += 1
        
#         return {
#             "status": "created",
#             "label": label,
#             "total_frames": len(frames),
#             "active_frames": len(active_frames),
#             "csv_files": csv_index
#         }
#     finally:
#         # ✅ 항상 임시파일 삭제
#         if os.path.exists(video_path):
#             os.remove(video_path)

# # 학습용 dataset 생성 함수(자동으로 폴더에서 파일을 읽는 경우)
# def create_dataset_from_folder():
    
#     folder = r"C:\Users\noua0\OneDrive\Desktop\calling_dataset"
    
#     for file in os.listdir(folder):

#         if not file.endswith(".mp4"):
#             continue
        
#         video_path = os.path.join(folder, file)
#         label = os.path.splitext(file)[0]
        
#         dataset_dir = os.path.join("dataset", label)
#         os.makedirs(dataset_dir, exist_ok=True)
        
#         cap = cv2.VideoCapture(video_path)
        
#         if not cap.isOpened():
#             logging.warning(f"비디오 파일을 열 수 없습니다: {file}")
#             continue
        
#         frames = []
        
#         while cap.isOpened():
#             ret, frame = cap.read()
#             if not ret:
#                 break
#             kp = extract_keypoints(frame)
#             frames.append(kp)
            
#         cap.release()
        
#         frames = np.array(frames)
        
#         active_frames = extract_active_frames(frames)
        
#         if active_frames is None:
#             logging.warning(f"활성 구간을 찾을 수 없습니다: {file}")
#             continue
        
#         window = 30
#         stride = 5
        
#         if len(active_frames) < window:
#             logging.warning(f"활성 구간이 너무 짧습니다: {file}")
#             continue
        
#         existing = len(os.listdir(dataset_dir))
#         csv_index = existing
        
#         for start in range(0, len(active_frames) - window + 1, stride):
            
#             seq = active_frames[start:start + window]
#             csv_path = os.path.join(dataset_dir, f"{label}_{csv_index}.csv")
            
#             with open(csv_path, "w", newline="") as f:
#                 writer = csv.writer(f)
#                 for row in seq:
#                     writer.writerow(row)
            
#             csv_index += 1

# # 학습용 dataset 자동 생성 api
# @app.get("/create/dataset/auto")
# async def create_dataset_auto():
#     try:
#         create_dataset_from_folder()
#         return {"status": "created"}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}

# # 학습용 dataset 로딩 함수
# def load_dataset():
    
#     x = []
#     y = []
    
#     dataset_path = "dataset"
#     label_list = os.listdir(dataset_path)
    
#     label_map = {lbl: i for i, lbl in enumerate(label_list)}
    
#     for lbl in label_list:
        
#         folder = os.path.join(dataset_path, lbl)
        
#         for file in os.listdir(folder):
            
#             if file.endswith(".csv"):
                
#                 path = os.path.join(folder, file)
#                 data = np.loadtxt(path, delimiter=",")
                
#                 x.append(data)
#                 y.append(label_map[lbl])
    
#     return np.array(x), np.array(y), label_list

# # 모델 정의 함수(생성, 학습)
# def train_model():
    
#     X, y, label_list = load_dataset()
    
#     num_classes = len(label_list)
    
#     y = tf.keras.utils.to_categorical(y, num_classes)
    
#     inputs = Input(shape=(30, 225))
    
#     x = MultiHeadAttention(num_heads=4, key_dim=64)(inputs, inputs)
#     x = LayerNormalization()(x)
#     x = GlobalAveragePooling1D()(x)
    
#     outputs = Dense(num_classes, activation="softmax")(x)
    
#     mdl = Model(inputs, outputs)
    
#     mdl.compile(
#         optimizer="adam",
#         loss="categorical_crossentropy",
#         metrics=["accuracy"]
#     )
    
#     mdl.fit(X, y, epochs=50)
    
#     mdl.save("sign_model.h5")
#     np.save("labels.npy", label_list)
    
# @app.get("/train")
# async def train():
#     try:
#         train_model()
#         return {"status": "model trained"}
#     except Exception as e:
#         return {"status": "error", "message": str(e)}
    
# @app.post("/predict/word")
# async def predict_word(file: UploadFile = File(...)):
#     # ✅ 모델 로드 확인
#     check_model_loaded()
    
#     # ✅ uuid로 임시파일명 충돌 방지
#     video_path = f"temp_{uuid.uuid4().hex}_{file.filename}"
#     try:
#         with open(video_path, "wb") as f:
#             f.write(await file.read())
            
#         cap = cv2.VideoCapture(video_path)
#         frames = []
        
#         while cap.isOpened():
#             ret, frame = cap.read()
#             if not ret:
#                 break
#             kp = extract_keypoints(frame)
#             frames.append(kp)
        
#         cap.release()
        
#         active_frames = extract_active_frames(np.array(frames))
        
#         if active_frames is None or len(active_frames) < 30:
#             return {"status": "error", "message": "수어 동작 구간을 찾을 수 없습니다"}
        
#         sequences = []
#         for start in range(0, len(active_frames) - 30 + 1, 5):
#             seq = np.array(active_frames[start:start + 30])
#             sequences.append(seq)
        
#         sequences = np.array(sequences)
#         preds = model.predict(sequences)
#         avg_pred = preds.mean(axis=0)
        
#         pred_label = labels[np.argmax(avg_pred)]
#         confidence = float(avg_pred[np.argmax(avg_pred)])
        
#         if confidence < 0.6:
#             return {"status": "uncertain", "prediction": pred_label, "confidence": confidence}
        
#         return {"status": "success", "prediction": pred_label, "confidence": confidence}
    
#     except Exception as e:
#         return {"status": "error", "message": str(e)}
#     finally:
#         # ✅ 항상 임시파일 삭제
#         if os.path.exists(video_path):
#             os.remove(video_path)
    
        
# def extract_frames_from_video(video_path):
#     cap = cv2.VideoCapture(video_path)
#     frames = []
    
#     while cap.isOpened():
#         ret, frame = cap.read()
#         if not ret:
#             break
#         kp = extract_keypoints(frame)
#         frames.append(kp)
    
#     cap.release()
    
#     return np.array(frames)
        
# # 문장 예측 내부 함수 (✅ 엔드포인트 핸들러와 이름 충돌 방지)
# def _predict_sentence(frames, mdl, lbls):
    
#     segments = split_segments_with_pause(frames)
    
#     sentences = []
    
#     for start, end in segments:
#         segment = frames[start:end]
        
#         if len(segment) < 30:
#             continue
        
#         words = predict_words_in_segment(segment, mdl, lbls)
        
#         if len(words) > 0:
#             sentence = " ".join(words)
#             sentences.append(sentence)
    
#     return sentences
        
# @app.post("/predict/sentence")
# async def predict_sentence_endpoint(file: UploadFile = File(...)):
#     # ✅ 모델 로드 확인
#     check_model_loaded()
    
#     try:
#         # ✅ delete=False + finally로 안전하게 삭제 (Windows 호환)
#         with tempfile.NamedTemporaryFile(delete=False, suffix=".mp4") as tmp:
#             tmp.write(await file.read())
#             tmp_path = tmp.name
        
#         try:
#             frames = extract_frames_from_video(tmp_path)
            
#             if len(frames) < 30:
#                 return {"status": "error", "message": "영상이 너무 짧습니다"}
            
#             words_list = _predict_sentence(frames, model, labels)
#             sentence = " ".join(words_list)
            
#             return {"status": "success", "words": words_list, "sentence": sentence}
        
#         finally:
#             if os.path.exists(tmp_path):
#                 os.remove(tmp_path)
    
#     except Exception as e:
#         return {"status": "error", "message": str(e)}
    
# # 음성 텍스트 반환 함수
# def extract_speech_list(video_path):
#     result = speech_model.transcribe(video_path)
    
#     speech_list = []
    
#     for seg in result["segments"]:
#         speech_list.append(seg["text"].strip())
    
#     return speech_list

# # 음성 텍스트 변환 api
# @app.post("/audio")
# async def audio(file: UploadFile = File(...)):
#     # ✅ uuid로 임시파일명 충돌 방지
#     video_path = f"temp_{uuid.uuid4().hex}_{file.filename}"
#     try:
#         with open(video_path, "wb") as f:
#             f.write(await file.read())
        
#         speech_list = extract_speech_list(video_path)
        
#         return {"status": "success", "speech": speech_list}
    
#     except Exception as e:
#         return {"status": "error", "message": str(e)}
#     finally:
#         # ✅ 항상 임시파일 삭제
#         if os.path.exists(video_path):
#             os.remove(video_path)