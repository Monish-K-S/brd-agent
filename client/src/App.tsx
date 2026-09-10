import { BrowserRouter, Route, Routes } from "react-router-dom"

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<div>Landing</div>} />
        <Route path="/login" element={<div>Login</div>} />
        <Route path="/signup" element={<div>Signup</div>} />
        <Route path="/workspaces" element={<div>Workspaces</div>} />
        <Route path="/workspaces/:id" element={<div>Workspace</div>} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
