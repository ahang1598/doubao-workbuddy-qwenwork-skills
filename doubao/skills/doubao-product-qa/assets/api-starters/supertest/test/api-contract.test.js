import fs from 'node:fs'
import Ajv from 'ajv'
import request from 'supertest'
import { describe, expect, it } from 'vitest'

const manifest = JSON.parse(fs.readFileSync('api-operations.json', 'utf8'))
const baseUrl = (process.env.QA_BASE_URL || '').replace(/\/$/, '')
const safeMethods = new Set(['GET', 'HEAD', 'OPTIONS'])
const ajv = new Ajv({ allErrors: true, strict: false })

function buildRequest(operation, testCase) {
  let path = operation.path
  const query = {}
  const headers = {}
  const cookies = []
  const omit = testCase.omit || {}
  for (const parameter of operation.parameters || []) {
    const omitted = omit.in === parameter.in && omit.name === parameter.name
    const value = omitted && parameter.in === 'path' ? '' : omitted ? undefined : parameter.value
    if (value === undefined || value === null) continue
    if (parameter.in === 'path') path = path.replace(`{${parameter.name}}`, String(value))
    if (parameter.in === 'query') query[parameter.name] = value
    if (parameter.in === 'header') headers[parameter.name] = String(value)
    if (parameter.in === 'cookie') cookies.push(`${parameter.name}=${encodeURIComponent(String(value))}`)
  }
  if (cookies.length) headers.Cookie = cookies.join('; ')
  if (testCase.kind !== 'unauthorized' && process.env.QA_API_TOKEN) {
    const name = process.env.QA_AUTH_HEADER || 'Authorization'
    const scheme = (process.env.QA_AUTH_SCHEME || 'Bearer').trim()
    headers[name] = `${scheme} ${process.env.QA_API_TOKEN}`.trim()
  }
  const body = testCase.kind === 'missing_body' ? undefined : operation.body
  return { path, query, headers, body }
}

describe('OpenAPI contract', () => {
  for (const operation of manifest.operations || []) {
    for (const testCase of operation.cases || []) {
      const built = buildRequest(operation, testCase)
      const shouldSkip = !baseUrl
        || (!safeMethods.has(operation.method) && process.env.QA_ALLOW_WRITES !== '1')
        || (operation.requires_auth && testCase.kind !== 'unauthorized' && !process.env.QA_API_TOKEN)
        || /\{[^}]+\}/.test(built.path)
      const register = shouldSkip ? it.skip : it
      register(testCase.case_id, async () => {
        let call = request(baseUrl)[operation.method.toLowerCase()](built.path).query(built.query).set(built.headers)
        if (built.body !== undefined && built.body !== null) call = call.send(built.body)
        const response = await call
        expect(testCase.expected_statuses).toContain(response.status)
        if (testCase.kind === 'happy' && operation.response_schema && response.body !== undefined) {
          const validate = ajv.compile(operation.response_schema)
          expect(validate(response.body), JSON.stringify(validate.errors)).toBe(true)
        }
      })
    }
  }
})
