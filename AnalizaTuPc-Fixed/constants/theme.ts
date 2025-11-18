import Colors from "./Colors";
import { Platform } from 'react-native';
export { Colors };

export const Fonts = {
  regular: "System",
  bold: "System-Bold",
  rounded: "System",
  mono: Platform.OS === 'ios' ? 'Courier New' : 'monospace'
} as const;

export type FontsType = typeof Fonts;
export default Fonts;