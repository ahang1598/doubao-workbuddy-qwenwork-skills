package com.dingtalk.plugin.filter;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import javax.servlet.Filter;
import javax.servlet.FilterChain;
import javax.servlet.ServletException;
import javax.servlet.ServletRequest;
import javax.servlet.ServletResponse;
import javax.servlet.http.HttpServletRequest;
import java.io.IOException;

/**
 * 请求日志过滤器：在 Servlet 层面拦截所有请求，打印请求信息。
 * 比 Controller 层的日志更早执行，可捕获 Spring MVC 反序列化失败等问题。
 */
@Slf4j
@Component
public class RequestLoggingFilter implements Filter {

    @Override
    public void doFilter(ServletRequest servletRequest, ServletResponse servletResponse, FilterChain chain)
            throws IOException, ServletException {

        HttpServletRequest httpRequest = (HttpServletRequest) servletRequest;
        String uri = httpRequest.getRequestURI();
        String method = httpRequest.getMethod();

        // 只对 /api/ 路径打印详细日志，避免静态资源噪音
        if (uri.startsWith("/api/")) {
            log.info("[Filter] 收到请求: {} {}, Content-Type={}, Timestamp={}, SignaturePresent={}",
                    method, uri,
                    httpRequest.getContentType(),
                    httpRequest.getHeader("Ding-Docs-Timestamp"),
                    httpRequest.getHeader("Ding-Docs-Signature") != null);
        }

        chain.doFilter(servletRequest, servletResponse);
    }
}
