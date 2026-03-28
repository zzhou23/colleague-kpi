import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 15000,
});

export default client;
