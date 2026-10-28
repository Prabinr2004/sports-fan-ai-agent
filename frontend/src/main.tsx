import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";
import "./styles.css";
import "./premium-football.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
import "./mobile-design.css";
import "./home-mobile.css";
import "./team-hub-mobile.css";
import "./matches-mobile.css";
import "./match-center-mobile.css";
import "./quiz-mobile.css";
