package com.example.jwt.domain.config.filter;

import com.example.jwt.domain.config.JwtTokenProvider;
import com.example.jwt.domain.user.service.CustomUserDetailsService;
import io.jsonwebtoken.ExpiredJwtException;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import lombok.RequiredArgsConstructor;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.stereotype.Component;
import org.springframework.web.filter.OncePerRequestFilter;

import java.io.IOException;

@Component
@RequiredArgsConstructor
public class JwtAuthenticationFilter extends OncePerRequestFilter {

    private final JwtTokenProvider jwtTokenProvider;
    private final CustomUserDetailsService userDetailsService;

    /**
     * 모든 요청마다 실행되는 필터
     */
    @Override
    protected void doFilterInternal(
            HttpServletRequest request,
            HttpServletResponse response,
            FilterChain filterChain
    ) throws ServletException, IOException {

        String accessToken = request.getHeader("Authorization");
        String refreshToken = request.getHeader("Refresh-Token");

        try {
            // Access Token 존재 + 유효
            if (accessToken != null) {
                accessToken = accessToken.replace("Bearer ", "");
                jwtTokenProvider.validateToken(accessToken);

                String email = jwtTokenProvider.getEmail(accessToken);
                setAuthentication(email);
            }
        } catch (ExpiredJwtException e) {
            // Access Token 만료 → Refresh Token 검사
            if (refreshToken != null) {
                jwtTokenProvider.validateToken(refreshToken);

                String email = jwtTokenProvider.getEmail(refreshToken);

                // 새로운 Access Token 발급
                String newAccessToken = jwtTokenProvider.createAccessToken(email);
                response.setHeader("Authorization", "Bearer " + newAccessToken);

                setAuthentication(email);
            } else {
                // Refresh Token 없음 → 401
                response.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
                return;
            }
        }

        filterChain.doFilter(request, response);
    }

    /**
     * SecurityContext 에 인증 정보 저장
     */
    private void setAuthentication(String email) {
        UserDetails userDetails = userDetailsService.loadUserByUsername(email);

        UsernamePasswordAuthenticationToken authentication =
                new UsernamePasswordAuthenticationToken(
                        userDetails,
                        null,
                        userDetails.getAuthorities()
                );

        SecurityContextHolder.getContext().setAuthentication(authentication);
    }
}

