package com.scenic.guide.common.result;

import com.fasterxml.jackson.annotation.JsonInclude;
import lombok.Data;

import java.io.Serializable;

/**
 * 统一返回结果
 */
@Data
@JsonInclude(JsonInclude.Include.NON_NULL)
public class Result<T> implements Serializable {

    private Integer code;
    private String message;
    private T data;

    public static <T> Result<T> ok() {
        return build(200, "success", null);
    }

    public static <T> Result<T> ok(T data) {
        return build(200, "success", data);
    }

    public static <T> Result<T> ok(String message, T data) {
        return build(200, message, data);
    }

    public static <T> Result<T> fail(String message) {
        return build(500, message, null);
    }

    public static <T> Result<T> fail(Integer code, String message) {
        return build(code, message, null);
    }

    public static <T> Result<T> unauthorized(String message) {
        return build(401, message, null);
    }

    public static <T> Result<T> forbidden(String message) {
        return build(403, message, null);
    }

    public static <T> Result<T> notFound(String message) {
        return build(404, message, null);
    }

    private static <T> Result<T> build(Integer code, String message, T data) {
        Result<T> r = new Result<>();
        r.setCode(code);
        r.setMessage(message);
        r.setData(data);
        return r;
    }

    public boolean isOk() {
        return this.code != null && this.code == 200;
    }
}
