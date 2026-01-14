package com.example.seven.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.security.access.hierarchicalroles.RoleHierarchy;
import org.springframework.security.access.hierarchicalroles.RoleHierarchyImpl;
import org.springframework.security.authorization.AuthorizationDecision;
import org.springframework.security.authorization.AuthorizationManager;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.access.intercept.RequestAuthorizationContext;

@Configuration
public class SecurityConfig {

    // 비밀번호 암호화용 Bean
    @Bean
    public PasswordEncoder passwordEncoder() {
        return new BCryptPasswordEncoder();
    }

    // role hierarchy
    @Bean
    public RoleHierarchy roleHierarchy() {

        return RoleHierarchyImpl.withRolePrefix("ROLE")
                .role("ADMIN").implies("USER")
                .build();
    }

    // 시큐리티 필터 구획을 내 마음대로 커스텀
    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http) {

        // 수많은 필터 중 CSRF 필터를 disable 시킴
//        http
//                .csrf(csrf -> csrf.disable());

//        csrf enable
        http
                .csrf(Customizer.withDefaults());

        // 특정 경로 csrf disable
        http
                .csrf(csrf -> csrf
                        .ignoringRequestMatchers("/logout"));
        // csrf 설정시 로그아웃은 무조건 post 요청만 허용되기 때문에 위 설정을 추가하기도 함.)
        // 허용한 프론트 url은 join.mustache, login.mustache 참고(토큰 사용법)

        // 로그인 필터 설정
        http
                .formLogin(login -> login
                        .loginProcessingUrl("/login")
                        .loginPage("/login"));

        // remember me 설정
        http
                .rememberMe(me -> me
                        .key("vsafsfesklrjvxvmxvsvs")
                        .rememberMeParameter("remember-me")
                        .tokenValiditySeconds(14 * 24 * 60 * 60)
                );

        // 인가 필터에 대한 설정
        http
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers("/").permitAll()
                        .requestMatchers("/join").permitAll()
                        .requestMatchers("/login").permitAll()
                        // 위에 role hierarchy처럼 user보다 admin이 높다고 선언하였으면
                        // .requestMatchers("/user").hasAnyRole("USER")
                        // 이렇게 작성하여도 admin이 user보다 높기에 접근이 가능하다.
                        .requestMatchers("/user").hasAnyRole("USER", "ADMIN")
                        // .requestMatchers("/admin").hasRole("ADMIN")
                        // 커스팀 인가
                        .requestMatchers("/admin").access(customAuthorizationManager())
                        // 위에서 선언하지 않은 모든 요청은 차단
                        .anyRequest().denyAll());

        // 세션
        // 기본 값은 설정이나 이 설정 추가 시 세션 사용 안함(JWT이용 시)
//        http
//                .sessionManagement(session -> session
//                        .sessionCreationPolicy(SessionCreationPolicy.STATELESS));

        // 세션 고정 공격을 방지하기위해 로그인이 성공하면 JESSIONID 값을 변경하도록 세팅
        http
                .sessionManagement(session -> session
                        .sessionFixation().changeSessionId());
        // 최종 빌드
        return http.build();
    }

    // 커스텀 인가
    private AuthorizationManager<RequestAuthorizationContext> customAuthorizationManager() {
        return (authentication, context) -> {

            boolean allowed =
                    authentication.get().getAuthorities().stream()
                            .anyMatch(a -> a.getAuthority().equals("ROLE_ADMIN"));

            // 지역 맞는지

            // 사용할 수 있는 카운트

            // 비즈니스, 개인


            return new AuthorizationDecision(allowed);
        };
    }
}
