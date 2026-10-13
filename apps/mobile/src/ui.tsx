import React from "react";
import {
  Alert,
  Pressable,
  StyleSheet,
  Text,
  View,
  TextInput,
  type ViewStyle,
} from "react-native";
import MaterialCommunityIcons from "@expo/vector-icons/MaterialCommunityIcons";
import * as Haptics from "expo-haptics";
export const C = {
  bg: "#091218",
  panel: "#111E28",
  raised: "#192B36",
  line: "#28404D",
  text: "#EEF6F8",
  muted: "#A4B7C1",
  cyan: "#5BDCF5",
  green: "#69E6BD",
  purple: "#BAA3FF",
  amber: "#FFCE78",
  red: "#FF8391",
};
export const T = StyleSheet.create({
  label: {
    color: C.muted,
    fontSize: 11,
    letterSpacing: 1.1,
    fontWeight: "700",
  },
  title: {
    color: C.text,
    fontSize: 23,
    fontWeight: "700",
    letterSpacing: -0.6,
  },
  body: { color: C.muted, fontSize: 13, lineHeight: 20 },
  row: { flexDirection: "row", alignItems: "center", gap: 8 },
  card: {
    backgroundColor: C.panel,
    borderRadius: 18,
    borderWidth: 1,
    borderColor: C.line,
    padding: 16,
  },
  value: {
    color: C.text,
    fontSize: 25,
    fontVariant: ["tabular-nums"],
    fontWeight: "600",
  },
  section: { color: C.text, fontSize: 17, fontWeight: "700", marginBottom: 12 },
  input: {
    backgroundColor: C.bg,
    borderColor: C.line,
    borderWidth: 1,
    borderRadius: 10,
    padding: 12,
    color: C.text,
    minHeight: 48,
    fontSize: 16,
    fontVariant: ["tabular-nums"],
  },
});
export function Icon({
  name,
  size = 23,
  color = C.text,
}: {
  name: string;
  size?: number;
  color?: string;
}) {
  return (
    <MaterialCommunityIcons name={name as any} size={size} color={color} />
  );
}
export function Action({
  icon,
  label,
  onPress,
  active = false,
  color,
  compact = false,
  disabled = false,
  style,
  testID,
}: {
  icon: string;
  label: string;
  onPress: () => void;
  active?: boolean;
  color?: string;
  compact?: boolean;
  disabled?: boolean;
  style?: ViewStyle;
  testID?: string;
}) {
  return (
    <Pressable
      testID={testID}
      accessibilityRole="button"
      accessibilityLabel={label}
      accessibilityState={{ disabled, selected: active }}
      disabled={disabled}
      onPress={() => {
        void Haptics.selectionAsync().catch(() => {});
        onPress();
      }}
      onLongPress={() => Alert.alert(label)}
      style={({ pressed }) => [
        {
          minWidth: 48,
          minHeight: 48,
          borderRadius: 13,
          backgroundColor: active ? C.raised : "transparent",
          alignItems: "center",
          justifyContent: "center",
          paddingHorizontal: compact ? 8 : 12,
          opacity: disabled ? 0.4 : pressed ? 0.6 : 1,
          gap: 3,
        },
        style,
      ]}
    >
      <Icon name={icon} color={color ?? (active ? C.cyan : C.muted)} />
      {!compact && (
        <Text
          numberOfLines={1}
          style={{
            color: active ? C.cyan : C.muted,
            fontSize: 10,
            fontWeight: "600",
          }}
        >
          {label}
        </Text>
      )}
    </Pressable>
  );
}
export function NumberField({
  label,
  value,
  unit,
  onChange,
}: {
  label: string;
  value: number;
  unit?: string;
  onChange: (v: number) => void;
}) {
  const [text, setText] = React.useState(String(value));
  React.useEffect(() => setText(String(value)), [value]);
  return (
    <View style={{ gap: 6, flex: 1, minWidth: 130 }}>
      <Text style={T.label}>
        {label} {unit ?? ""}
      </Text>
      <TextInput
        accessibilityLabel={`${label} ${unit ?? ""}`}
        keyboardType="numeric"
        selectTextOnFocus
        value={text}
        onChangeText={setText}
        onEndEditing={() => {
          const n = Number(text.replace(",", "."));
          if (text.trim() && Number.isFinite(n)) {
            onChange(n);
          } else setText(String(value));
        }}
        style={T.input}
      />
    </View>
  );
}
export function Note({
  children,
  color = C.amber,
}: {
  children: React.ReactNode;
  color?: string;
}) {
  return (
    <View
      style={{
        flexDirection: "row",
        gap: 9,
        backgroundColor: C.panel,
        padding: 12,
        borderRadius: 12,
      }}
    >
      <Icon name="information-outline" size={18} color={color} />
      <Text style={[T.body, { flex: 1, color, fontSize: 12 }]}>{children}</Text>
    </View>
  );
}
export const number = (v: number | undefined, digits = 2) =>
  v === undefined || !Number.isFinite(v)
    ? "—"
    : Math.abs(v) >= 1e6
      ? v.toExponential(2).replace(".", ",")
      : v.toFixed(digits).replace(".", ",");
