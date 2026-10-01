import first from "./company-1.json"
import second from "./company-2.json"
import third from "./company-3.json"
import fourth from "./company-4.json"
import fifth from "./company-5.json"
import sixth from "./company-6.json"
import request from "./request.json"

export const demoPayload = {
  ...request,
  companies: [first, second, fifth, third, fourth, sixth],
}
