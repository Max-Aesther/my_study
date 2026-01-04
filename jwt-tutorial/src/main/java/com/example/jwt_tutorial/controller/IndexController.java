package com.example.jwt_tutorial.controller;

import com.example.jwt_tutorial.dto.JoinDTO;
import com.example.jwt_tutorial.entity.UserEntity;
import com.example.jwt_tutorial.repository.UserRepository;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.ArrayList;
import java.util.List;

@RestController
public class IndexController {


    private final UserRepository userRepository;

    public IndexController(UserRepository userRepository) {
        this.userRepository = userRepository;
    }

    @GetMapping("/index")
    public List<JoinDTO> userIndex() {
        List<JoinDTO> joinDTOList = new ArrayList<>();
        List<UserEntity> userEntityList = userRepository.findAll();

        for (UserEntity user : userEntityList) {
            JoinDTO joinDTO = new JoinDTO();
            joinDTO.setUsername(user.getUsername());
            joinDTO.setPassword(user.getPassword());
            joinDTOList.add(joinDTO);
        }

        return joinDTOList;
    }
}
