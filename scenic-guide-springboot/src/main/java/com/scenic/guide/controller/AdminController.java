package com.scenic.guide.controller;

import com.scenic.guide.common.result.PageResult;
import com.scenic.guide.common.result.Result;
import com.scenic.guide.entity.AvatarConfig;
import com.scenic.guide.entity.FAQ;
import com.scenic.guide.entity.KnowledgeDoc;
import com.scenic.guide.entity.Spot;
import com.scenic.guide.service.impl.AdminService;
import com.scenic.guide.service.impl.ScenicService;
import io.swagger.annotations.Api;
import io.swagger.annotations.ApiOperation;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.io.File;
import java.io.IOException;
import java.util.*;

/**
 * 管理后台 Controller
 */
@Api(tags = "管理后台")
@Slf4j
@RestController
@RequestMapping("/admin")
@RequiredArgsConstructor
public class AdminController {

    private final AdminService adminService;
    private final ScenicService scenicService;

    @Value("${file.upload-dir}")
    private String uploadDir;

    @Value("${file.static-dir}")
    private String staticDir;

    // ====== 知识库管理 ======

    @ApiOperation("获取知识库文档列表")
    @GetMapping("/knowledge/list")
    public Result<PageResult<Map<String, Object>>> listKnowledgeDocs(
            @RequestParam(defaultValue = "1") int page,
            @RequestParam(defaultValue = "20") int size,
            @RequestParam(required = false) String status) {
        return Result.ok(adminService.listKnowledgeDocs(page, size, status));
    }

    @ApiOperation("上传文档到知识库")
    @PostMapping("/knowledge/upload")
    public Result<Map<String, Object>> uploadDocument(
            @RequestParam("file") MultipartFile file,
            @RequestParam(defaultValue = "") String title,
            @RequestParam(defaultValue = "general") String category) throws IOException {

        String[] allowedTypes = {".pdf", ".docx", ".doc", ".txt", ".md"};
        String originalFilename = file.getOriginalFilename() != null ? file.getOriginalFilename() : "";
        String ext = originalFilename.contains(".") ?
                originalFilename.substring(originalFilename.lastIndexOf(".")).toLowerCase() : "";
        if (!Arrays.asList(allowedTypes).contains(ext)) {
            return Result.fail(400, "不支持的文件类型: " + ext);
        }

        new File(uploadDir).mkdirs();
        String fileId = UUID.randomUUID().toString();
        String savedPath = uploadDir + "/" + fileId + ext;
        file.transferTo(new File(savedPath));

        KnowledgeDoc doc = new KnowledgeDoc();
        doc.setTitle(title.isEmpty() ? originalFilename : title);
        doc.setFileName(originalFilename);
        doc.setFileType(ext.replaceFirst("\\.", ""));
        doc.setFilePath(savedPath);
        doc.setCategory(category);
        doc.setStatus("done");
        doc.setChunkCount(0);
        adminService.saveKnowledgeDoc(doc);

        return Result.ok(Map.of("message", "文件上传成功", "docId", doc.getId(), "fileId", fileId));
    }

    @ApiOperation("直接添加文本知识")
    @PostMapping("/knowledge/text")
    public Result<Map<String, Object>> addTextKnowledge(
            @RequestParam String title,
            @RequestParam String content,
            @RequestParam(defaultValue = "general") String category) {

        KnowledgeDoc doc = new KnowledgeDoc();
        doc.setTitle(title);
        doc.setFileType("text");
        doc.setContentPreview(content.substring(0, Math.min(200, content.length())));
        doc.setChunkCount(1);
        doc.setStatus("done");
        doc.setCategory(category);
        adminService.saveKnowledgeDoc(doc);

        return Result.ok(Map.of("message", "知识添加成功", "chunkCount", 1));
    }

    @ApiOperation("删除知识库文档")
    @DeleteMapping("/knowledge/{docId}")
    public Result<Map<String, Object>> deleteDocument(@PathVariable Long docId) {
        adminService.deleteKnowledgeDoc(docId);
        return Result.ok(Map.of("message", "删除成功"));
    }

    // ====== FAQ 管理 ======

    @ApiOperation("获取FAQ列表")
    @GetMapping("/faq/list")
    public Result<Map<String, Object>> listFAQs(@RequestParam(required = false) String category) {
        return Result.ok(Map.of("faqs", adminService.listFAQs(category)));
    }

    @ApiOperation("创建FAQ")
    @PostMapping("/faq/create")
    public Result<Map<String, Object>> createFAQ(@RequestBody FAQ faq) {
        Long id = adminService.createFAQ(faq);
        return Result.ok(Map.of("message", "FAQ创建成功", "id", id));
    }

    @ApiOperation("更新FAQ")
    @PutMapping("/faq/{faqId}")
    public Result<Map<String, Object>> updateFAQ(@PathVariable Long faqId, @RequestBody FAQ faq) {
        adminService.updateFAQ(faqId, faq);
        return Result.ok(Map.of("message", "FAQ更新成功"));
    }

    @ApiOperation("删除FAQ")
    @DeleteMapping("/faq/{faqId}")
    public Result<Map<String, Object>> deleteFAQ(@PathVariable Long faqId) {
        adminService.deleteFAQ(faqId);
        return Result.ok(Map.of("message", "删除成功"));
    }

    // ====== 数字人配置 ======

    @ApiOperation("获取数字人形象列表")
    @GetMapping("/avatar/list")
    public Result<Map<String, Object>> listAvatars() {
        List<String> voices = List.of("zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural",
                "zh-CN-XiaohanNeural", "zh-CN-YunjianNeural");
        return Result.ok(Map.of("avatars", adminService.listAvatars(), "availableVoices", voices));
    }

    @ApiOperation("更新数字人配置")
    @PutMapping("/avatar/{avatarId}")
    public Result<Map<String, Object>> updateAvatar(@PathVariable Long avatarId,
                                                     @RequestBody AvatarConfig data) {
        adminService.updateAvatar(avatarId, data);
        return Result.ok(Map.of("message", "配置更新成功"));
    }

    @ApiOperation("上传数字人形象图片")
    @PostMapping("/avatar/{avatarId}/upload-image")
    public Result<Map<String, Object>> uploadAvatarImage(
            @PathVariable Long avatarId,
            @RequestParam("file") MultipartFile file) throws IOException {
        new File(staticDir + "/avatar").mkdirs();
        String originalFilename = file.getOriginalFilename() != null ? file.getOriginalFilename() : "avatar.png";
        String ext = originalFilename.contains(".") ?
                originalFilename.substring(originalFilename.lastIndexOf(".")).toLowerCase() : ".png";
        String filename = "avatar_" + avatarId + "_" + UUID.randomUUID().toString().replace("-", "").substring(0, 8) + ext;
        String savePath = staticDir + "/avatar/" + filename;
        file.transferTo(new File(savePath));

        String imageUrl = "/static/avatar/" + filename;
        AvatarConfig update = new AvatarConfig();
        update.setImageUrl(imageUrl);
        adminService.updateAvatar(avatarId, update);

        return Result.ok(Map.of("message", "图片上传成功", "imageUrl", imageUrl));
    }

    // ====== 景点管理（管理后台）======

    @ApiOperation("获取景点列表（管理端）")
    @GetMapping("/scenic/spots")
    public Result<List<Map<String, Object>>> listSpots(@RequestParam(required = false) Long scenicId) {
        return Result.ok(scenicService.listSpotsForAdmin(scenicId));
    }

    @ApiOperation("创建景点")
    @PostMapping("/scenic/spots")
    public Result<Map<String, Object>> createSpot(@RequestBody Spot spot) {
        scenicService.createSpot(spot);
        return Result.ok(Map.of("message", "景点创建成功", "id", spot.getId()));
    }

    @ApiOperation("更新景点")
    @PutMapping("/scenic/spots/{id}")
    public Result<Map<String, Object>> updateSpot(@PathVariable Long id, @RequestBody Spot spot) {
        scenicService.updateSpot(id, spot);
        return Result.ok(Map.of("message", "景点更新成功"));
    }

    @ApiOperation("删除景点")
    @DeleteMapping("/scenic/spots/{id}")
    public Result<Map<String, Object>> deleteSpot(@PathVariable Long id) {
        scenicService.deleteSpot(id);
        return Result.ok(Map.of("message", "删除成功"));
    }

    // ====== 数据分析 ======

    @ApiOperation("数据大屏概览")
    @GetMapping("/analytics/overview")
    public Result<Map<String, Object>> analyticsOverview(@RequestParam(defaultValue = "7") int days) {
        return Result.ok(adminService.getAnalyticsOverview(days));
    }

    @ApiOperation("情感趋势分析")
    @GetMapping("/analytics/emotion-trend")
    public Result<Map<String, Object>> emotionTrend(@RequestParam(defaultValue = "7") int days) {
        return Result.ok(adminService.getEmotionTrend(days));
    }

    @ApiOperation("热门问题统计")
    @GetMapping("/analytics/hot-questions")
    public Result<Map<String, Object>> hotQuestions(@RequestParam(defaultValue = "10") int limit) {
        return Result.ok(adminService.getHotQuestions(limit));
    }

    @ApiOperation("每日统计数据")
    @GetMapping("/analytics/daily-stats")
    public Result<Map<String, Object>> dailyStats(@RequestParam(defaultValue = "14") int days) {
        return Result.ok(adminService.getDailyStats(days));
    }
}
