package com.example.jwt.domain.user.repository;

import com.example.jwt.domain.user.entity.UserEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.Optional;

public interface UserRepository extends JpaRepository<UserEntity, Long> {
    /**
     * JWT 안에는 email만 넣기 때문에
     * 토큰 검증 시 email로 사용자 조회
     */
    Optional<UserEntity> findByEmail(String email);
}
