package com.example.jwt.domain.user.entity;

import jakarta.persistence.*;
import lombok.AllArgsConstructor;
import lombok.Builder;
import lombok.Getter;
import lombok.NoArgsConstructor;

@Entity
@Table(name = "users")
@Getter
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class UserEntity {

    /**
     * 대표 PK
     * 1부터 자동 증가
     */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /**
     * 로그인 ID 역할
     */
    @Column(nullable = false, unique = true)
    private String email;

    /**
     * 암호화된 비밀번호
     */
    @Column(nullable = false)
    private String password;

    /**
     * 소셜 로그인 여부
     */
    @Column(nullable = false)
    private boolean isSocial;

    /**
     * 닉네임
     */
    @Column(nullable = false)
    private String nickname;
}

