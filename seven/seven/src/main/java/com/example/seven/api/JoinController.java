package com.example.seven.api;

import com.example.seven.domain.user.dto.UserRequestDTO;
import com.example.seven.domain.user.service.UserService;
import org.springframework.stereotype.Controller;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;

@Controller
public class JoinController {

    private final UserService userService;

    public JoinController(UserService userService) {
        this.userService = userService;
    }

    // 회원 가입 데이터 처리 메소드
    @PostMapping("/join")
    public String join(UserRequestDTO dto) {
        userService.join(dto);

        return "redirect:/";
    }

    // 회원 가입 페이지 제공 메소드
    @GetMapping("/join")
    public String joinPage() {
        return "join";
    }
}
