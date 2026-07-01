using System.Collections.Generic;
using UnityEngine;

namespace BallGame.Pinball
{
    public sealed class PinballDropSlotRewardController : MonoBehaviour
    {
        [SerializeField] private int[] lightCountWeights = { 15, 30, 35, 20 };
        [SerializeField] private int[] rewardsByLightCount = { 8, 5, 3, 2 };

        private readonly List<PinballDropSlot> slots = new List<PinballDropSlot>();
        private bool resolvingBall;
        private int currentLightCount;

        public void RegisterSlot(PinballDropSlot slot)
        {
            if (slot != null && !slots.Contains(slot))
            {
                slots.Add(slot);
            }
        }

        private void Start()
        {
            PinballGameController.Instance?.RegisterDropSlotRewardController(this);
            StartNewRound();
        }

        public void StartNewRound()
        {
            if (slots.Count == 0)
            {
                return;
            }

            resolvingBall = false;
            currentLightCount = PickLightCount();
            ClearLights();
            LightRandomSlots(currentLightCount);

            PinballGameController.Instance?.SetStatus($"Red slots: {currentLightCount} | reward: +{GetReward()} balls");
        }

        public void ResolveSlot(PinballDropSlot slot)
        {
            if (resolvingBall || slot == null)
            {
                return;
            }

            resolvingBall = true;
            if (slot.IsLit)
            {
                int reward = GetReward();
                slot.SetLit(false);
                PinballGameController.Instance?.AwardBonusBalls(reward, "Red slot hit");
                PinballGameController.Instance?.DrainBall($"Red slot hit +{reward} balls");
            }
            else
            {
                PinballGameController.Instance?.DrainBall("Blank slot");
            }
        }

        private int PickLightCount()
        {
            int maxLightCount = Mathf.Min(slots.Count, rewardsByLightCount.Length);
            if (maxLightCount <= 1)
            {
                return 1;
            }

            // The design keeps at least one unlit slot so the player always reads risk.
            maxLightCount = Mathf.Min(maxLightCount, slots.Count - 1);
            int totalWeight = 0;
            for (int i = 0; i < maxLightCount; i++)
            {
                totalWeight += Mathf.Max(0, GetWeight(i));
            }

            if (totalWeight <= 0)
            {
                return 1;
            }

            int roll = Random.Range(0, totalWeight);
            for (int i = 0; i < maxLightCount; i++)
            {
                roll -= Mathf.Max(0, GetWeight(i));
                if (roll < 0)
                {
                    return i + 1;
                }
            }

            return 1;
        }

        private int GetWeight(int zeroBasedLightCount)
        {
            if (lightCountWeights == null || zeroBasedLightCount >= lightCountWeights.Length)
            {
                return 0;
            }

            return lightCountWeights[zeroBasedLightCount];
        }

        private int GetReward()
        {
            int index = Mathf.Clamp(currentLightCount - 1, 0, rewardsByLightCount.Length - 1);
            return rewardsByLightCount[index];
        }

        private void ClearLights()
        {
            for (int i = 0; i < slots.Count; i++)
            {
                slots[i].SetLit(false);
            }
        }

        private void LightRandomSlots(int lightCount)
        {
            List<int> availableIndices = new List<int>(slots.Count);
            for (int i = 0; i < slots.Count; i++)
            {
                availableIndices.Add(i);
            }

            for (int i = 0; i < lightCount && availableIndices.Count > 0; i++)
            {
                int pick = Random.Range(0, availableIndices.Count);
                int slotIndex = availableIndices[pick];
                availableIndices.RemoveAt(pick);
                slots[slotIndex].SetLit(true);
            }
        }
    }
}
