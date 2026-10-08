package com.scenic.guide.controller;

import com.scenic.guide.common.result.Result;
import com.scenic.guide.dto.request.LoginRequest;
import com.scenic.guide.dto.response.LoginResponse;
import com.scenic.guide.entity.User;
import com.scenic.guide.service.AuthService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.Authentication;
import org.springframework.validation.annotation.Validated;
import org.springframework.web.bind.annotation.*;

/**
 * 认证 Controller
 */
@Api(tags = "认证管理")
@RestController
@RequestMapping("/admin/auth")
@RequiredArgsConstructor
public class AuthController {

    private final AuthService authService;

    @ApiOperation("管理员登录")
    @PostMapping("/login")
    public Result<LoginResponse> login(@Validated @RequestBody LoginRequest request) {
        LoginResponse response = authService.login(request);
        return Result.ok("登录成功", response);
    }

    @ApiOperation("获取当前用户信息")
    @GetMapping("/me")
    public Result<Object> getCurrentUser(Authentication authentication) {
        if (authentication == null) {
            return Result.unauthorized("未登录");
        }
        String username = (String) authentication.getPrincipal();
        User user = authService.getCurrentUser(username);
        return Result.ok(java.util.Map.of(
            "username", user.getUsername(),
            "role", user.getRole(),
            "email", user.getEmail() != null ? user.getEmail() : ""
        ));
    }
}
