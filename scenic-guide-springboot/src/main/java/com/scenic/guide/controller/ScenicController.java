package com.scenic.guide.controller;

import com.scenic.guide.common.result.Result;
import com.scenic.guide.entity.Spot;
import com.scenic.guide.service.impl.ScenicService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.*;

/**
 * 景区景点 Controller（公开接口）
 */
@Api(tags = "景区景点")
@RestController
@RequestMapping("/scenic")
@RequiredArgsConstructor
public class ScenicController {

    private final ScenicService scenicService;

    @ApiOperation("获取景区基本信息")
    @GetMapping("/info")
    public Result<Map<String, Object>> getScenicInfo() {
        return Result.ok(scenicService.getScenicInfo());
    }

    @ApiOperation("获取所有景点列表")
    @GetMapping("/spots")
    public Result<Map<String, Object>> getAllSpots(@RequestParam(required = false) Long scenicId) {
        List<Map<String, Object>> spots = scenicService.getAllSpots(scenicId);
        return Result.ok(Map.of("spots", spots));
    }

    @ApiOperation("获取景点详情")
    @GetMapping("/spots/{id}")
    public Result<Map<String, Object>> getSpotDetail(@PathVariable Long id) {
        return Result.ok(scenicService.getSpotDetail(id));
    }

    @ApiOperation("获取附近景点（GPS定位）")
    @GetMapping("/nearby")
    public Result<Map<String, Object>> getNearbySpots(
            @RequestParam double lat,
            @RequestParam double lng,
            @RequestParam(defaultValue = "200.0") double radius) {
        return Result.ok(scenicService.getNearbySpots(lat, lng, radius));
    }

    @ApiOperation("创建景点（管理端）")
    @PostMapping("/spots")
    public Result<Spot> createSpot(@RequestBody Spot spot) {
        scenicService.createSpot(spot);
        return Result.ok("创建成功", spot);
    }

    @ApiOperation("更新景点（管理端）")
    @PutMapping("/spots/{id}")
    public Result<Spot> updateSpot(@PathVariable Long id, @RequestBody Spot spot) {
        scenicService.updateSpot(id, spot);
        return Result.ok("更新成功", spot);
    }

    @ApiOperation("删除景点（管理端）")
    @DeleteMapping("/spots/{id}")
    public Result<Void> deleteSpot(@PathVariable Long id) {
        scenicService.deleteSpot(id);
        return Result.ok("删除成功", null);
    }

    @Value("${file.image-dir:d:/TalkingV2/图片}")
    private String imageDir;

    @ApiOperation("上传景点图片")
    @PostMapping("/spots/{id}/upload-image")
    public Result<Map<String, Object>> uploadSpotImage(
            @PathVariable Long id,
            @RequestParam("file") MultipartFile file) throws IOException {

        // 检查文件类型
        String originalFilename = file.getOriginalFilename();
        if (originalFilename == null || originalFilename.isEmpty()) {
            return Result.fail("文件名不能为空");
        }
        String ext = originalFilename.substring(originalFilename.lastIndexOf(".")).toLowerCase();
        if (!Arrays.asList(".jpg", ".jpeg", ".png", ".gif", ".webp").contains(ext)) {
            return Result.fail("不支持的图片格式: " + ext);
        }

        // 保存到用户图片目录
        Path basePath = Paths.get(imageDir).toAbsolutePath().normalize();
        File dir = basePath.toFile();
        if (!dir.exists()) {
            dir.mkdirs();
        }

        // 使用景点ID + 时间戳生成唯一文件名
        String filename = "spot_" + id + "_" + System.currentTimeMillis() + ext;
        File destFile = new File(dir, filename);
        file.transferTo(destFile);

        // 更新数据库中的 images 字段
        String imageUrl = "/spot-images/" + filename;
        scenicService.updateSpotImage(id, imageUrl);

        Map<String, Object> result = new HashMap<>();
        result.put("url", imageUrl);
        result.put("filename", filename);
        result.put("size", file.getSize());
        return Result.ok("图片上传成功", result);
    }
}
