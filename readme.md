## machine-learning(2025.03)
실행 시 streamlit run을 사용하여 실행하시면 됩니다.
python 버전: python 3.10.6
2025.08.25 딥 러닝 모델 추가

## jwt-tutorial(2025.08)
post localhost:8080/join     body값 : username: admin  password: 1234
post localhost:8080/login   header부분에서 authentication jwt토큰 값 확인
get  localhost:8080/admin   header부분에 authentication jwt토큰 값 기입
순으로 실행 시 정상적으로 jwt 인증 확인
세션은 STATELESS 상태로 두었습니다.

## flask api(2025.09)
python: 3.10.6
flask서버를 구현하여 jwt 로그인, 회원가입, 책 반납, 조회, 등록, 대출 등을 구현하였습니다.
관련 클라이언트 테스트 파일도 함께 첨부되어있습니다.

## redis(2025.12)
redis 관련 명령어 및 구조에 대한 공부 진행

## docker(2026.01)
docker 구조, 명령어, 컨테이너, githubAction 등(다음 프로젝트 진행 시 배포 및 CI/CD 파이프 라인 등을 직접 구현해보고자 공부,  redis역시 동일)

## spring-security7(2026.01)
java: 21
spring security 7이 업데이트 되었다 하여 간단하게 로그인 회원 가입 등 필요한 부분만 설정하여 재구현해보았습니다.(jwt가 아닌
.csrf 토큰 등)
전에 배운 docker를 활용하여 docker build 및 compose하여 관련파일이 없어도 실행할 수 있게끔 구현해보았습니다.

## jwt(2026.01)
java: 21
spring security 7에 이어 access토큰 및 jwt토큰 로직을 추가구현

## kubernetes(eks), github action 등 추가 공부하여 간단한 프론트 백엔드 구현 후 배포하여 실제 클라우드 환경 경험 예정.

## eks 2026/01
eks(kubernetes)+ rds(mysql)을 연동하여 spring서버 배포를 진행해보았습니다.(https인증서 연결 및 github action연동하여 진행, docker이미지는 ecr을 활용하여 진행, 도메인은 가비아에서 구입)

## fastapi 2026/01
의료 회사에서 인턴으로 근무를 하고 있어 의료 관련된 간단한 백엔드 로직을 fastapi를 사용하여 구현하였습니다.
jwt(refrsh token: 14일(db저장 로그아웃 및 토큰 만료시 none처리), access token: 10분(클라이언트에 저장(서버간 통신은 헤더로 주고받음)) db: firebase, python: 3.13.11, 관련 firebase키값, .env에 값들은 일부 존재하지 않습니다.)
이메일 인증 체크 로직 구현, ai프롬프트 작성(open ai 사용)

## opencv 2026/04
python: 3.11.6
opencv 및 mediapipe를 활용하여 수어 번역 프로그램을 만들고 있었습니다.
프레임 단위 및 슬라이딩 윈도우를 활용하여 단어 영상 학습 및 예측은 구현하였으나, 문장 번역의 경우 단어 경계를 구분하기 애매하여 CTC기술을 적용해보아
모델을 재구성하여 문장까지도 학습 및 예측이 되게끔 구현할 예정입니다.
(원래는 관련된 프로젝트를 진행 중이라 구현을 하게 되었는데 도중 해산의 문제로 시간이 될 때 추후 업데이트 할 계획입니다. 현재는 다른 공부를 생각 중에 있습니다.)