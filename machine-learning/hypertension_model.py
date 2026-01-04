#!/usr/bin/env python
# coding: utf-8
# In[32]:
import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import train_test_split, GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.metrics import accuracy_score
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns
import joblib
import streamlit as st
# 폰트 지정
plt.rcParams['font.family'] = 'Malgun Gothic'
# 마이너스 부호 깨짐 지정
plt.rcParams['axes.unicode_minus'] = False
# 숫자가 지수표현식으로 나올 때 지정
pd.options.display.float_format = '{:.2f}'.format
# In[33]:
# 데이터 로드
dataset = pd.read_csv('dataset/Hypertension-risk-model-main.csv')
dataset = dataset.dropna()
# In[34]:
# 변수별 상관관계 히트맵
plt.figure(figsize=(10, 8))
sns.heatmap(dataset.corr(), annot=True, cmap='coolwarm')
plt.title('상관관계 히트맵')
plt.show()
# In[35]:
# feature와 target분리
X = dataset.drop('Risk', axis=1)
y = dataset['Risk']
# 훈련 데이터 및 테스트 데이터로 분류
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
# 고혈압 특성 중요도 모델 생성 및 학습
model = LinearRegression()
model.fit(X_train, y_train)
# In[39]:
y_pred = model.predict(X_test)
# In[40]:
# # 모델 평가
print("\n모델 성능:")
print("R² 점수:", r2_score(y_test, y_pred))
print("평균 제곱 오차 (MSE):", mean_squared_error(y_test, y_pred))
print("평균 절대 오차 (MAE):", mean_absolute_error(y_test, y_pred))
# In[41]:
# 고혈압 데이터의 특성 중요도 분석
feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': np.abs(model.coef_)
})
feature_importance = feature_importance.sort_values('importance', ascending=False)
print("\n특성 중요도:")
print(feature_importance)
# In[42]:
# 시각화: 고혈압 데이터의 특성 중요도
plt.figure(figsize=(5, 6))
sns.barplot(x='importance', y='feature', data=feature_importance)
plt.title('고혈압 데이터의 특성 중요도')
plt.xlabel('특성 중요도')
plt.tight_layout()
plt.show()
# In[43]:
# 특성 중요도를 이용하여 feature 재설정
X = dataset[['BPMeds', 'diabetes', 'male', 'sysBP', 'currentSmoker']]
y = dataset['Risk']
# In[46]:
# 훈련 데이터 및 테스트 데이터 분류
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
# In[47]:
# 재설정된 데이터를 기반으로 모델 생성 및 학습(고혈압 체크 모델, 랜덤포레스트 사용)
rf_model = RandomForestClassifier(n_estimators=30, random_state=42)
rf_model.fit(X_train, y_train)
# In[48]:
# 예측
y_pred_rf = rf_model.predict(X_test)
# In[49]:
# 랜덤 포레스트 평가
print("랜덤 포레스트 성능:")
print(f"정확도: {accuracy_score(y_test, y_pred_rf):.2f}")
print("분류 보고서:\n", classification_report(y_test, y_pred_rf))
print("혼동 행렬:\n", confusion_matrix(y_test, y_pred_rf))
# 고혈압 진단 후 합병증(뇌졸증) 예측 모델
# 데이터 로드
data = pd.read_csv('dataset/healthcare-dataset-stroke-data.csv')
data = data.dropna()
data = data.drop(['id'], axis=1)
data['gender'] = data['gender'].apply(lambda x: 1 if x == '남성' else 0)
# In[57]:
# feature, target 분리
X = data[['age', 'hypertension', 'heart_disease', 'avg_glucose_level', 'bmi', 'gender']]
y = data['stroke']
# 훈련 데이터 및 테스트 데이터 나누기
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
# 합병증(뇌졸증) 특성 분포도 모델 생성 및 학습
st_model = LinearRegression()
st_model.fit(X_train, y_train)
# 뇌졸증 특성 중요도
feature_importance = pd.DataFrame({
    'feature': X.columns,
    'importance': np.abs(st_model.coef_)
})
feature_importance = feature_importance.sort_values('importance', ascending=False)
# 뇌졸증 특성 시각화
plt.figure(figsize=(10, 6))
sns.barplot(x='importance', y='feature', data=feature_importance)
plt.title('Feature Importance in Diabetes Prediction')
plt.xlabel('Absolute Cefficient Value')
plt.tight_layout()
plt.show()
# In[64]:
# 특성 중요도에 의해서 데이터 재설정
X = data[['heart_disease', 'hypertension', 'age', 'bmi']]
y = data['stroke']
# In[65]:
# 훈련 데이터 및 테스트 데이터 분할
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
# In[66]:
# 뇌졸증 예측 모델 생성 및 학습
st_reg_model = RandomForestClassifier(random_state=42)
st_reg_model.fit(X_train, y_train)
# In[67]:
# 예측 및 정확도 평가
y_pred = st_reg_model.predict(X_test)
acc = accuracy_score(y_test, y_pred)
print(f'모델 정확도: {acc * 100:.2f}%')
joblib.dump(rf_model, 'hypertension_model.pkl') # 고혈압 예측 데이터
joblib.dump(st_reg_model, 'stroke_model.pkl') # 뇌졸증 예측 데이터터
# Streamlit 앱
st.title('고혈압 예측 시스템')
st.write('BPMeds, diabetes, male, sysBP, currentSmoker, heart_disease 값을 입력하여 고혈압 예측을 해보세요')
# 사용자 입력받기
BPMeds = st.radio("혈압약을 복용중입니까?", ["예", "아니오"])
diabetes = ("당뇨병이 있습니까?", ["예", "아니오"])
male = st.radio("남성입니까?", ["예", "아니오"])
sysBP = st.slider('sysBP (수축기 혈압)', min_value=80.0, max_value=200.0, value=100.0, step=0.5)
currentSmoker = st.radio("흡연자입니까?", ["예", "아니오"])
age = st.slider('나이', min_value=1, max_value=100, value=10)
bmi = st.slider('bmi (체질량지수)', min_value=10.00, max_value=40.00, value=22.00, step=0.1)
# 선택지를 내부적으로 1과 0으로 변환
BPMeds = 1 if BPMeds == "예" else 0
diabetes = 1 if diabetes == "예" else 0
male = 1 if male == "예" else 0
currentSmoker = 1 if currentSmoker == "예" else 0
# 세션 상태 초기화
if "prediction_result" not in st.session_state:
    st.session_state.prediction_result = None
if "heart_disease" not in st.session_state:
    st.session_state.heart_disease = None
if "stroke_checked" not in st.session_state:
    st.session_state.stroke_checked = False
if "prediction_result2" not in st.session_state:
    st.session_state.prediction_result2 = None
if "age" not in st.session_state:
    st.session_state.age = 0
if "bmi" not in st.session_state:
    st.session_state.bmi = 0
    
# 예측하기 버튼
if st.button('예측'):
    rf_model = joblib.load('hypertension_model.pkl')
    input_data = np.array([[BPMeds, diabetes, male, sysBP, currentSmoker]])
    prediction = rf_model.predict(input_data)[0]
    st.session_state.prediction_result = prediction
    st.session_state.stroke_checked = False
    st.session_state.age = age
    st.session_state.bmi = bmi
    
# 심장 질환 값 변경 시 기존 값 세팅
if st.session_state.prediction_result == 1:
    st.write('예측 결과: 고혈압 가능성이 높습니다.')
    st.write('고혈압 가능성이 높기에 합병증(뇌졸증) 검사를 실시합니다.')
    heart_disease = st.radio("심장 질환을 보유하고 있습니까?", ["예", "아니오"])
    st.session_state.heart_disease = 1  if heart_disease == "예" else 0
elif st.session_state.prediction_result == 0:
    st.write('예측 결과: 고혈압 가능성이 낮습니다.')
    st.session_state.heart_disease = None
    
# 뇌졸증 예측버튼
if st.session_state.heart_disease != None and st.button('뇌졸증 예측'):
    st_reg_model = joblib.load('stroke_model.pkl')
    input_data2 = np.array([[st.session_state.heart_disease, st.session_state.prediction_result, st.session_state.age, st.session_state.bmi]])
    prediction2 = st_reg_model.predict(input_data2)[0]
    st.session_state.prediction_result2 = prediction2
    st.session_state.stroke_checked = True
# 뇌졸중 결과 출력
if st.session_state.stroke_checked:
    if st.session_state.prediction_result2 == 1:
        st.write("예측 결과: 뇌졸증 가능성이 높습니다.")
    else:
        st.write("예측 결과: 뇌졸증 가능성이 낮습니다.")
    