package com.scenic.guide.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.scenic.guide.common.exception.BusinessException;
import com.scenic.guide.entity.Scenic;
import com.scenic.guide.entity.Spot;
import com.scenic.guide.mapper.ScenicMapper;
import com.scenic.guide.mapper.SpotMapper;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.util.*;

/**
 * 景区景点 Service
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ScenicService {

    private final ScenicMapper scenicMapper;
    private final SpotMapper spotMapper;

    public Map<String, Object> getScenicInfo() {
        Scenic scenic = scenicMapper.selectOne(new LambdaQueryWrapper<Scenic>()
                .eq(Scenic::getIsActive, true)
                .last("LIMIT 1"));
        if (scenic == null) {
            Map<String, Object> def = new HashMap<>();
            def.put("name", "云山风景区");
            def.put("description", "国家AAAAA级旅游景区");
            def.put("address", "广东省广州市白云区");
            def.put("openTime", "08:00-19:00");
            def.put("ticketPrice", "成人票80元");
            return def;
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", scenic.getId());
        result.put("name", scenic.getName());
        result.put("description", scenic.getDescription());
        result.put("address", scenic.getAddress());
        result.put("latitude", scenic.getLatitude());
        result.put("longitude", scenic.getLongitude());
        result.put("openTime", scenic.getOpenTime());
        result.put("ticketPrice", scenic.getTicketPrice());
        result.put("phone", scenic.getPhone());
        return result;
    }

    public List<Map<String, Object>> getAllSpots(Long scenicId) {
        LambdaQueryWrapper<Spot> wrapper = new LambdaQueryWrapper<Spot>()
                .eq(Spot::getIsActive, true)
                .orderByAsc(Spot::getOrderNum);
        if (scenicId != null) {
            wrapper.eq(Spot::getScenicId, scenicId);
        }
        List<Spot> spots = spotMapper.selectList(wrapper);
        List<Map<String, Object>> result = new ArrayList<>();
        for (Spot s : spots) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("id", s.getId());
            item.put("scenicId", s.getScenicId());
            item.put("name", s.getName());
            item.put("description", s.getDescription());
            item.put("guideText", s.getGuideText());
            item.put("latitude", s.getLatitude());
            item.put("longitude", s.getLongitude());
            item.put("triggerRadius", s.getTriggerRadius());
            item.put("orderNum", s.getOrderNum());
            item.put("durationMinutes", s.getDurationMinutes());
            item.put("category", s.getCategory());
            item.put("icon", s.getIcon());
            item.put("openTime", s.getOpenTime());
            item.put("price", s.getPrice());
            item.put("images", s.getImages());
            item.put("audioUrl", s.getAudioUrl());
            item.put("isActive", s.getIsActive());
            result.add(item);
        }
        return result;
    }

    public Map<String, Object> getSpotDetail(Long spotId) {
        Spot spot = spotMapper.selectById(spotId);
        if (spot == null || Boolean.FALSE.equals(spot.getIsActive())) {
            throw BusinessException.notFound("景点不存在");
        }
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("id", spot.getId());
        result.put("name", spot.getName());
        result.put("description", spot.getDescription());
        result.put("guideText", spot.getGuideText());
        result.put("latitude", spot.getLatitude());
        result.put("longitude", spot.getLongitude());
        result.put("triggerRadius", spot.getTriggerRadius());
        result.put("durationMinutes", spot.getDurationMinutes());
        result.put("category", spot.getCategory());
        result.put("images", spot.getImages());
        result.put("audioUrl", spot.getAudioUrl());
        return result;
    }

    public Map<String, Object> getNearbySpots(double lat, double lng, double radius) {
        List<Spot> allSpots = spotMapper.selectList(new LambdaQueryWrapper<Spot>()
                .eq(Spot::getIsActive, true));
        List<Map<String, Object>> nearby = new ArrayList<>();
        for (Spot spot : allSpots) {
            if (spot.getLatitude() == null || spot.getLongitude() == null) continue;
            double dist = haversine(lat, lng, spot.getLatitude(), spot.getLongitude());
            double triggerDist = spot.getTriggerRadius() != null ? spot.getTriggerRadius() : 50.0;
            if (dist <= Math.max(radius, triggerDist)) {
                Map<String, Object> item = new LinkedHashMap<>();
                item.put("id", spot.getId());
                item.put("name", spot.getName());
                item.put("distance", Math.round(dist * 10.0) / 10.0);
                item.put("latitude", spot.getLatitude());
                item.put("longitude", spot.getLongitude());
                item.put("triggered", dist <= triggerDist);
                item.put("guideText", spot.getGuideText() != null ?
                        spot.getGuideText().substring(0, Math.min(100, spot.getGuideText().length())) + "..." : "");
                item.put("audioUrl", spot.getAudioUrl());
                nearby.add(item);
            }
        }
        nearby.sort(Comparator.comparingDouble(m -> (Double) m.get("distance")));
        Map<String, Object> result = new LinkedHashMap<>();
        result.put("currentLocation", Map.of("lat", lat, "lng", lng));
        result.put("nearbySpots", nearby);
        result.put("triggeredSpots", nearby.stream().filter(m -> Boolean.TRUE.equals(m.get("triggered"))).collect(java.util.stream.Collectors.toList()));
        return result;
    }

    // Haversine 距离计算（米）
    private double haversine(double lat1, double lng1, double lat2, double lng2) {
        double R = 6371000;
        double dLat = Math.toRadians(lat2 - lat1);
        double dLng = Math.toRadians(lng2 - lng1);
        double a = Math.sin(dLat / 2) * Math.sin(dLat / 2)
                + Math.cos(Math.toRadians(lat1)) * Math.cos(Math.toRadians(lat2))
                * Math.sin(dLng / 2) * Math.sin(dLng / 2);
        double c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        return R * c;
    }

    // ====== 管理后台 CRUD ======

    public List<Map<String, Object>> listScenicForAdmin() {
        List<Scenic> list = scenicMapper.selectList(new LambdaQueryWrapper<Scenic>()
                .orderByDesc(Scenic::getId));
        List<Map<String, Object>> result = new ArrayList<>();
        for (Scenic s : list) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("id", s.getId());
            item.put("name", s.getName());
            item.put("address", s.getAddress());
            item.put("openTime", s.getOpenTime());
            item.put("ticketPrice", s.getTicketPrice());
            item.put("isActive", s.getIsActive());
            result.add(item);
        }
        return result;
    }

    public List<Map<String, Object>> listSpotsForAdmin(Long scenicId) {
        LambdaQueryWrapper<Spot> wrapper = new LambdaQueryWrapper<Spot>()
                .orderByAsc(Spot::getOrderNum);
        if (scenicId != null) wrapper.eq(Spot::getScenicId, scenicId);
        List<Spot> list = spotMapper.selectList(wrapper);
        List<Map<String, Object>> result = new ArrayList<>();
        for (Spot s : list) {
            Map<String, Object> item = new LinkedHashMap<>();
            item.put("id", s.getId());
            item.put("scenicId", s.getScenicId());
            item.put("name", s.getName());
            item.put("description", s.getDescription());
            item.put("guideText", s.getGuideText());
            item.put("category", s.getCategory());
            item.put("icon", s.getIcon());
            item.put("openTime", s.getOpenTime());
            item.put("price", s.getPrice());
            item.put("orderNum", s.getOrderNum());
            item.put("durationMinutes", s.getDurationMinutes());
            item.put("latitude", s.getLatitude());
            item.put("longitude", s.getLongitude());
            item.put("triggerRadius", s.getTriggerRadius());
            item.put("isActive", s.getIsActive());
            result.add(item);
        }
        return result;
    }

    public void createSpot(Spot spot) {
        spot.setIsActive(true);
        if (spot.getTriggerRadius() == null) spot.setTriggerRadius(50.0);
        if (spot.getOrderNum() == null) spot.setOrderNum(0);
        if (spot.getDurationMinutes() == null) spot.setDurationMinutes(5);
        spotMapper.insert(spot);
    }

    public void updateSpot(Long id, Spot spot) {
        spot.setId(id);
        spotMapper.updateById(spot);
    }

    public void deleteSpot(Long id) {
        Spot spot = spotMapper.selectById(id);
        if (spot == null) throw BusinessException.notFound("景点不存在");
        spot.setIsActive(false);
        spotMapper.updateById(spot);
    }

    public void updateSpotImage(Long id, String imageUrl) {
        Spot spot = spotMapper.selectById(id);
        if (spot == null) throw BusinessException.notFound("景点不存在");
        // images 字段存储为 JSON 数组
        List<String> images = new ArrayList<>();
        if (spot.getImages() instanceof List) {
            images.addAll((List<String>) spot.getImages());
        }
        images.add(imageUrl);
        spot.setImages(images);
        spotMapper.updateById(spot);
    }
}
