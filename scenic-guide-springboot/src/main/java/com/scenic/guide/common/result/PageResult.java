package com.scenic.guide.common.result;

import lombok.Data;
import lombok.EqualsAndHashCode;

import java.util.List;

/**
 * 分页返回结果
 */
@Data
@EqualsAndHashCode(callSuper = false)
public class PageResult<T> {
    private Long total;
    private Integer page;
    private Integer size;
    private List<T> items;

    public static <T> PageResult<T> of(Long total, Integer page, Integer size, List<T> items) {
        PageResult<T> result = new PageResult<>();
        result.setTotal(total);
        result.setPage(page);
        result.setSize(size);
        result.setItems(items);
        return result;
    }
}
