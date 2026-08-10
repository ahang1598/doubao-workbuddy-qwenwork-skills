package qa.generated;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import io.restassured.RestAssured;
import io.restassured.http.Method;
import io.restassured.response.Response;
import io.restassured.specification.RequestSpecification;
import org.junit.jupiter.api.Assumptions;
import org.junit.jupiter.api.DynamicTest;
import org.junit.jupiter.api.TestFactory;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.stream.Stream;

import static io.restassured.module.jsv.JsonSchemaValidator.matchesJsonSchema;
import static org.junit.jupiter.api.Assertions.assertTrue;

class ApiContractTest {
    private static final ObjectMapper JSON = new ObjectMapper();
    private static final Set<String> SAFE_METHODS = Set.of("GET", "HEAD", "OPTIONS");

    @TestFactory
    Stream<DynamicTest> contractCases() throws Exception {
        JsonNode manifest = JSON.readTree(new File("api-operations.json"));
        List<DynamicTest> tests = new ArrayList<>();
        for (JsonNode operation : manifest.path("operations")) {
            for (JsonNode testCase : operation.path("cases")) {
                tests.add(DynamicTest.dynamicTest(testCase.path("case_id").asText(), () -> execute(operation, testCase)));
            }
        }
        return tests.stream();
    }

    private void execute(JsonNode operation, JsonNode testCase) throws Exception {
        String baseUrl = System.getenv("QA_BASE_URL");
        Assumptions.assumeTrue(baseUrl != null && !baseUrl.isBlank(), "未设置 QA_BASE_URL");
        String method = operation.path("method").asText();
        Assumptions.assumeTrue(SAFE_METHODS.contains(method) || "1".equals(System.getenv("QA_ALLOW_WRITES")), "写接口默认禁用");
        String token = System.getenv("QA_API_TOKEN");
        Assumptions.assumeTrue(!operation.path("requires_auth").asBoolean() || "unauthorized".equals(testCase.path("kind").asText()) || token != null, "缺少 QA_API_TOKEN");

        String path = operation.path("path").asText();
        RequestSpecification request = RestAssured.given().baseUri(baseUrl).contentType("application/json");
        JsonNode omit = testCase.path("omit");
        for (JsonNode parameter : operation.path("parameters")) {
            boolean omitted = omit.path("in").asText().equals(parameter.path("in").asText()) && omit.path("name").asText().equals(parameter.path("name").asText());
            JsonNode valueNode = parameter.path("value");
            if (omitted && !"path".equals(parameter.path("in").asText())) continue;
            String value = omitted ? "" : valueNode.isValueNode() ? valueNode.asText() : valueNode.toString();
            String name = parameter.path("name").asText();
            switch (parameter.path("in").asText()) {
                case "path" -> path = path.replace("{" + name + "}", value);
                case "query" -> request.queryParam(name, value);
                case "header" -> request.header(name, value);
                case "cookie" -> request.cookie(name, value);
            }
        }
        Assumptions.assumeFalse(path.matches(".*\\{[^}]+}.*"), "缺少路径参数样例");
        if (!"unauthorized".equals(testCase.path("kind").asText()) && token != null) {
            String header = System.getenv().getOrDefault("QA_AUTH_HEADER", "Authorization");
            String scheme = System.getenv().getOrDefault("QA_AUTH_SCHEME", "Bearer").trim();
            request.header(header, (scheme + " " + token).trim());
        }
        if (!"missing_body".equals(testCase.path("kind").asText()) && !operation.path("body").isMissingNode() && !operation.path("body").isNull()) {
            request.body(JSON.writeValueAsString(operation.path("body")));
        }
        Response response = request.request(Method.valueOf(method), path);
        List<Integer> expected = new ArrayList<>();
        testCase.path("expected_statuses").forEach(value -> expected.add(value.asInt()));
        assertTrue(expected.contains(response.statusCode()), () -> "实际状态=" + response.statusCode() + " body=" + response.asString());
        if ("happy".equals(testCase.path("kind").asText()) && !operation.path("response_schema").isMissingNode() && !operation.path("response_schema").isNull() && !response.asString().isBlank()) {
            response.then().body(matchesJsonSchema(operation.path("response_schema").toString()));
        }
    }
}
