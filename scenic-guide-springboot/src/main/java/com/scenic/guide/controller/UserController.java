package com.scenic.guide.controller;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.scenic.guide.common.exception.BusinessException;
import com.scenic.guide.common.result.Result;
import com.scenic.guide.entity.User;
import com.scenic.guide.mapper.UserMapper;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/**
 * 员工管理 Controller（仅超级管理员可用）
 */
@Api(tags = "员工管理")
@Slf4j
@RestController
@RequestMapping("/admin/users")
@RequiredArgsConstructor
public class UserController {

    private final UserMapper userMapper;
    private final PasswordEncoder passwordEncoder;

    @ApiOperation("获取所有员工列表")
    @GetMapping("/list")
    public Result<List<Map<String, Object>>> listUsers() {
        List<User> users = userMapper.selectList(
                new LambdaQueryWrapper<User>().orderByAsc(User::getId)
        );
        List<Map<String, Object>> result = users.stream().map(u -> Map.<String, Object>of(
                "id", u.getId(),
                "username", u.getUsername(),
                "email", u.getEmail() != null ? u.getEmail() : "",
                "role", u.getRole(),
                "isActive", u.getIsActive() != null ? u.getIsActive() : true,
                "createdAt", u.getCreatedAt() != null ? u.getCreatedAt().toString() : ""
        )).collect(Collectors.toList());
        return Result.ok(result);
    }

    @ApiOperation("创建员工账号")
    @PostMapping("/create")
    public Result<Map<String, Object>> createUser(@RequestBody Map<String, String> body) {
        String username = body.get("username");
        String password = body.get("password");
        String email = body.getOrDefault("email", "");
        String role = body.getOrDefault("role", "admin");

        if (username == null || username.isBlank()) {
            return Result.fail(400, "用户名不能为空");
        }
        if (password == null || password.length() < 6) {
            return Result.fail(400, "密码长度不能少于6位");
        }
        // 角色只允许 admin（普通管理员），不允许创建 super_admin
        if ("super_admin".equals(role)) {
            return Result.fail(400, "不能创建超级管理员账号");
        }

        // 检查用户名是否已存在
        Long count = userMapper.selectCount(
                new LambdaQueryWrapper<User>().eq(User::getUsername, username)
        );
        if (count > 0) {
            return Result.fail(400, "用户名已存在");
        }

        User user = new User();
        user.setUsername(username);
        user.setEmail(email.isBlank() ? null : email);
        user.setHashedPassword(passwordEncoder.encode(password));
        user.setRole(role);
        user.setIsActive(true);
        userMapper.insert(user);

        log.info("创建员工账号: username={}, role={}", username, role);
        return Result.ok(Map.of("message", "账号创建成功", "id", user.getId()));
    }

    @ApiOperation("更新员工信息")
    @PutMapping("/{id}")
    public Result<Map<String, Object>> updateUser(
            @PathVariable Long id,
            @RequestBody Map<String, Object> body) {

        User user = userMapper.selectById(id);
        if (user == null) {
            return Result.fail(404, "员工不存在");
        }
        // 超管账号不允许降权或禁用
        if ("super_admin".equals(user.getRole())) {
            return Result.fail(400, "不能修改超级管理员账号");
        }

        if (body.containsKey("email")) {
            String email = (String) body.get("email");
            user.setEmail(email == null || email.isBlank() ? null : email);
        }
        if (body.containsKey("isActive")) {
            user.setIsActive((Boolean) body.get("isActive"));
        }
        if (body.containsKey("password")) {
            String newPwd = (String) body.get("password");
            if (newPwd != null && newPwd.length() >= 6) {
                user.setHashedPassword(passwordEncoder.encode(newPwd));
            }
        }

        userMapper.updateById(user);
        log.info("更新员工账号: id={}", id);
        return Result.ok(Map.of("message", "更新成功"));
    }

    @ApiOperation("删除员工账号")
    @DeleteMapping("/{id}")
    public Result<Map<String, Object>> deleteUser(@PathVariable Long id) {
        User user = userMapper.selectById(id);
        if (user == null) {
            return Result.fail(404, "员工不存在");
        }
        if ("super_admin".equals(user.getRole())) {
            return Result.fail(400, "不能删除超级管理员账号");
        }

        userMapper.deleteById(id);
        log.info("删除员工账号: id={}, username={}", id, user.getUsername());
        return Result.ok(Map.of("message", "删除成功"));
    }

    @ApiOperation("重置员工密码")
    @PostMapping("/{id}/reset-password")
    public Result<Map<String, Object>> resetPassword(
            @PathVariable Long id,
            @RequestBody Map<String, String> body) {

        User user = userMapper.selectById(id);
        if (user == null) {
            return Result.fail(404, "员工不存在");
        }
        String newPwd = body.get("password");
        if (newPwd == null || newPwd.length() < 6) {
            return Result.fail(400, "密码长度不能少于6位");
        }

        user.setHashedPassword(passwordEncoder.encode(newPwd));
        userMapper.updateById(user);
        return Result.ok(Map.of("message", "密码重置成功"));
    }
}
