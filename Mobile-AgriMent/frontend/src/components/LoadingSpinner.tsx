import React, { useEffect, useRef } from "react";
import { View, Text, StyleSheet, Animated, Easing } from "react-native";

interface LoadingSpinnerProps {
  message?: string;
  subMessage?: string;
}

const ANALYSIS_STEPS = [
  "Analyzing your image...",
  "Identifying insect...",
  "Generating recommendation...",
];

export function LoadingSpinner({
  message,
  subMessage,
}: LoadingSpinnerProps) {
  const rotateAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const [stepIndex, setStepIndex] = React.useState(0);

  useEffect(() => {
    const rotation = Animated.loop(
      Animated.timing(rotateAnim, {
        toValue: 1,
        duration: 2000,
        easing: Easing.linear,
        useNativeDriver: true,
      })
    );

    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1.2,
          duration: 800,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 800,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ])
    );

    rotation.start();
    pulse.start();

    return () => {
      rotation.stop();
      pulse.stop();
    };
  }, []);

  useEffect(() => {
    if (!message) {
      const interval = setInterval(() => {
        setStepIndex((prev) => (prev + 1) % ANALYSIS_STEPS.length);
      }, 2500);
      return () => clearInterval(interval);
    }
  }, [message]);

  const rotate = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ["0deg", "360deg"],
  });

  const displayMessage = message || ANALYSIS_STEPS[stepIndex];

  return (
    <View style={styles.container}>
      <Animated.View
        style={[
          styles.spinnerOuter,
          { transform: [{ rotate }, { scale: pulseAnim }] },
        ]}
      >
        <View style={styles.spinnerInner}>
          <Animated.Text style={styles.bugIcon}>🐛</Animated.Text>
        </View>
      </Animated.View>

      <Text style={styles.message}>{displayMessage}</Text>
      {subMessage && <Text style={styles.subMessage}>{subMessage}</Text>}

      <View style={styles.dots}>
        {[0, 1, 2].map((i) => (
          <Animated.View
            key={i}
            style={[
              styles.dot,
              i === stepIndex && styles.activeDot,
            ]}
          />
        ))}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    padding: 40,
  },
  spinnerOuter: {
    width: 120,
    height: 120,
    borderRadius: 60,
    borderWidth: 4,
    borderColor: "#E8F5E9",
    borderTopColor: "#2E7D32",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 32,
  },
  spinnerInner: {
    width: 80,
    height: 80,
    borderRadius: 40,
    backgroundColor: "#E8F5E9",
    alignItems: "center",
    justifyContent: "center",
  },
  bugIcon: {
    fontSize: 40,
  },
  message: {
    fontSize: 18,
    fontWeight: "600",
    color: "#2E7D32",
    textAlign: "center",
    marginBottom: 8,
  },
  subMessage: {
    fontSize: 14,
    color: "#757575",
    textAlign: "center",
    marginBottom: 24,
  },
  dots: {
    flexDirection: "row",
    gap: 8,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#E0E0E0",
  },
  activeDot: {
    backgroundColor: "#2E7D32",
    width: 24,
  },
});
