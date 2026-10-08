package com.scenic.guide.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.scenic.guide.common.exception.BusinessException;
import com.scenic.guide.dto.request.LoginRequest;
import com.scenic.guide.dto.response.LoginResponse;
import com.scenic.guide.entity.User;
import com.scenic.guide.mapper.UserMapper;
import com.scenic.guide.service.AuthService;
import com.scenic.guide.util.JwtUtil;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;

/**
 * 认证 Service 实现
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class AuthServiceImpl implements AuthService {

    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;
    private final JwtUtil jwtUtil;

    @Override
    public LoginResponse login(LoginRequest request) {
        User user = userMapper.selectOne(new LambdaQueryWrapper<User>()
                .eq(User::getUsername, request.getUsername()));

        if (user == null || !passwordEncoder.matches(request.getPassword(), user.getHashedPassword())) {
            throw BusinessException.unauthorized("用户名或密码错误");
        }
        if (Boolean.FALSE.equals(user.getIsActive())) {
            throw new BusinessException(403, "账户已被禁用");
        }

        String token = jwtUtil.generateToken(user.getUsername(), user.getRole());

        return LoginResponse.builder()
                .accessToken(token)
                .tokenType("bearer")
                .username(user.getUsername())
                .role(user.getRole())
                .build();
    }

    @Override
    public User getCurrentUser(String username) {
        User user = userMapper.selectOne(new LambdaQueryWrapper<User>()
                .eq(User::getUsername, username));
        if (user == null) {
            throw BusinessException.notFound("用户不存在");
        }
        return user;
    }
}
