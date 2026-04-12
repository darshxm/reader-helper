import { createTheme } from "@mui/material/styles";

const theme = createTheme({
  palette: {
    mode: "dark",
    primary: {
      main: "#4a9eff",
    },
    background: {
      default: "#1a1a1a",
      paper: "#252525",
    },
    divider: "#444",
    text: {
      primary: "#e0e0e0",
      secondary: "#999",
    },
    error: {
      main: "#ff6b6b",
    },
    success: {
      main: "#4caf50",
    },
  },
  typography: {
    fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif',
    fontSize: 14,
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 500,
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        root: {
          "& fieldset": { borderColor: "#555" },
          "&:hover fieldset": { borderColor: "#777" },
        },
      },
    },
    MuiSelect: {
      styleOverrides: {
        root: {
          fontSize: 13,
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          textTransform: "none",
          fontWeight: 500,
          minHeight: 44,
        },
      },
    },
    MuiCssBaseline: {
      styleOverrides: {
        body: {
          overflow: "hidden",
          height: "100vh",
        },
        // Scrollbars
        "*::-webkit-scrollbar": { width: 6, height: 6 },
        "*::-webkit-scrollbar-track": { background: "#1a1a1a" },
        "*::-webkit-scrollbar-thumb": { background: "#444", borderRadius: 3 },
        "*::-webkit-scrollbar-thumb:hover": { background: "#666" },
      },
    },
  },
});

export default theme;
