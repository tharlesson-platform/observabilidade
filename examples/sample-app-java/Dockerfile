FROM maven:3.9.13-eclipse-temurin-25@sha256:ade3c87e3cdfbe04932afa16b31814cbf60b0122d21d78a76530684a1eeb7cc2 AS build
WORKDIR /src
COPY pom.xml /src/pom.xml
COPY src /src/src
RUN mvn -q -DskipTests package
ARG OTEL_JAVAAGENT_SHA256=4cff4ab46179260a61fc0d884f3f170cfbd9d2962dd260be2cff31262d0c7618
RUN curl --fail --silent --show-error --location --retry 3 \
      https://repo.maven.apache.org/maven2/io/opentelemetry/javaagent/opentelemetry-javaagent/2.11.0/opentelemetry-javaagent-2.11.0.jar \
      -o /src/opentelemetry-javaagent.jar \
    && echo "${OTEL_JAVAAGENT_SHA256}  /src/opentelemetry-javaagent.jar" | sha256sum --check --strict

FROM eclipse-temurin:25-jre-alpine@sha256:e1898fd6a11fc965a994d8ace186fd3585aeb636cf8f05f47a723fcfee0b0918
WORKDIR /app
COPY --from=build /src/target/sample-app-java-1.0.0.jar /app/app.jar
COPY --from=build /src/opentelemetry-javaagent.jar /app/opentelemetry-javaagent.jar

ENV PORT=8080
ENV OTEL_SERVICE_NAME=sample-app-java
ENV JAVA_TOOL_OPTIONS="-javaagent:/app/opentelemetry-javaagent.jar"
EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD wget -qO- http://localhost:8080/healthz || exit 1

USER 10001:10001
CMD ["java", "-jar", "/app/app.jar"]
