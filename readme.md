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
flask서버를 구현하여 jwt 로그인, 회원가입, 책 반납, 조회, 등록, 대출 등을 구현하였습니다.
관련 클라이언트 테스트 파일도 함께 첨부되어있습니다.

## redis(2025.12)
redis 관련 명령어 및 구조에 대한 공부 진행

## docker(2026.01)
docker 구조, 명령어, 컨테이너, githubAction 등(다음 프로젝트 진행 시 배포 및 CI/CD 파이프 라인 등을 직접 구현해보고자 공부,  redis역시 동일)

## spring-security7(2026.01)
spring security 7이 업데이트 되었다 하여 간단하게 로그인 회원 가입 등 필요한 부분만 설정하여 재구현해보았습니다.(jwt가 아닌
.csrf 토큰 등)
전에 배운 docker를 활용하여 docker build 및 compose하여 관련파일이 없어도 실행할 수 있게끔 구현해보았습니다.

## jwt(2026.01)
spring security 7에 이어 access토큰 및 jwt토큰 로직을 추가구현

## kubernetes(eks), github action 등 추가 공부하여 간단한 프론트 백엔드 구현 후 배포하여 실제 클라우드 환경 경험 예정.