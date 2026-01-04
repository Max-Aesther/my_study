# redis는 0~15번까지의 database로 구성
select db번호

# 데이터베이스 내 모든 키 조회
keys *

# 일반적인 String구조
# set을 통해 key:value 세팅
set user:email:1 hong1@naver.com
# nx : 이미 존재하며 pass, 없으면 set
set user:email:2 hong2@naver.com nx
# ex(expiration) : 만료시간(초단위), ttl(time to live)
set user:email:3 hong3@naver.com ex 10

# redis활용 : 사용자 인증정보 저장(ex-refresh토큰)
set user:1:refresh_token eyjaxabaalsdkal ex 100000

# 특정 key삭제
del user:email:1
# 현재 DB내 모든 key삭제
flushdb

# redis활용 : 좋아요기능 구현 
set likes:posting:1 0
incr likes:posting:1 #특정 key값의 value를 1만큼 증가
decr likes:posting:1 #특정 key값의 value를 1만큼 감소
get likes:posting:1

# redis활용: 재고관리
set stocks:product:1 100
decr stocks:product:1
get stocks:product:1

# redis활용 : 캐싱(임시저장) 기능 구현
set posting:1 "{\"title\":\"hello java\", \"contents\":\"hello java is ...\", \"author_email\":\"hong@naver.com\"}" ex 1000

# list자료구조 : redis의 list는 deque자료구조
# lpush : 데이터를 왼쪽 끝에 삽입
# rpush : 데이터를 오른쪽 끝에 삽입
# lpop :  데이터를 왼족에서 꺼내기(이때 그 값은 삭제됨)
# rpop : 데이터를 오른쪽에서 꺼내기(이때 그 값은 삭제됨)

lpush hongildongs hong1
lpush hongildongs hong2
rpush hongildongs hong3
rpop hongildongs
lpop hongildongs

# list조회
# -1은 리스트의 끝자리(마지막index)를 의미. -2는 끝에서 2번째를 의미
lrange hongildongs 0 0 #첫번째 값만 조회
lrange hongildongs -1 -1 #마지막 값만 조회
lrange hongildongs 0 -1 #처음부터 끝까지
lrange hongildongs -2 -1 #마지막2번째부터 마지막자리까지
lrange hongildongs 0 1 #처음부터 2번째까지

# 데이터 개수 조회
llen hongildongs
# ttl 적용
expire hongildongs 20
# ttl 조회
ttl hongildongs

# redis 활용 : 최근 방문한 페이지, 최근 조회한 상품목록
rpush mypages www.naver.com
rpush mypages www.google.com
rpush mypages www.daum.net
rpush mypages www.chatgpt.com
rpush mypages www.daum.com
# 최근방문한 페이지 3개만 보여주는
lrange mypages -3 -1

# set자료구조 : 중복없음, 순서없음
# set에 값 추가
sadd memberlist member1
sadd memberlist member2
sadd memberlist member3
# set 조회
smembsers memberlist
# set 요소의 개수 조회
scard memberlist
# set에서 멤버 제거
srem memberlist member2
# 특정 요소가 set안에 들어있는지 확인
sismember memberlist member1

# redis set활용 : 좋아요 구현
sadd likes:posting:1 member1
sadd likes:posting:1 member2
sadd likes:posting:1 member1
# 좋아요 개수
scard likes:posting:1
# 좋아요 눌렀는지 안눌렀는지 확인
sismember likes:posting:1 member1

# zset : sorted set
# add하는 score를 부여하고 , score를 기준으로 정렬
zadd memberlist 3 member1
zadd memberlist 4 member2
zadd memberlist 1 member3
zadd memberlist 2 member4

# 조회방법 : 기본적으로 socre기준 오름차순정렬
zrange memberlist 0 -1
# 내림차순 정렬
zrevrange memberlist 0 -1

# zset 요소 삭제
zrem memberlist member4

# zrank : 특정 멤버가 몇번째 순서인지 출력 (오름차순 기준)
zrank memberlist member2

# redis zset 활용 : 최근 본 상품목록
# zset를 활용해서 최근시간순으로 score를 설정하여 정렬
zadd recent:products 151930 pineapple
zadd recent:products 152030 banana
zadd recent:products 152130 orange
zadd recent:products 152230 apple
# zset도 set이므로 같은 상품을 add할 경우엔 시간만 업데이트되고 중복이 제거
zadd recent:products 152330 apple
# 최근 본 상품목록 3개조회
zrevrange recent:products 0 2
# score까지 포함하여 전체 데이터 조회시
zrevrange recent:products 0 -1 withscores

# hash : map형태의 자료구조, value값이 {key:value, key:value ...}
hset member:info:1 name hong email hong@naver.com age 30
# 특정요소 조회
hget member:info:1 name
# 모든 요소값 조회
hgetall member:info:1
# 특정 요소값만 수정
hset member:info:1 name kim
# 특정 요소값의 값을 증가/감소 시킬경우
 hincrby member:info:1 age 3
 hincrby member:info:1 age -3

# redis hash 활용 예시 : 빈번하게 변경되는 객체값 캐싱
# json형태의 문자열로 캐싱을 할경우, 해당 문자값을 수정할때에는 문자열을 파싱하여 통째로 변경해야함.

# redis pub sub 실습
# pub/sub 기능은 멀티 서버 환경에서 채팅, 알림 등의 서비스를 구현할때 많이 사용
# 터미널 2,3 실행
subscribe test_channel
# 터미널 1 실행
publish test_channel "hello, this is a test message."

# redis stream 실습 : 데이터 실시간으로 read, 데이터가 저장
# * : ID값 자동 생성
xadd test_stream * message "hello this is stream message"
# $ : 현재 마지막 메시지 이후에 오는 새 메시지를 의미.
xread block 20000 streams test_stream $
# - + : 전체 메시지 조회
xrange test_stream - +