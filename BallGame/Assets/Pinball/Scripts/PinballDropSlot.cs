using UnityEngine;

namespace BallGame.Pinball
{
    [RequireComponent(typeof(Collider2D))]
    public sealed class PinballDropSlot : MonoBehaviour
    {
        [SerializeField] private SpriteRenderer lightRenderer;
        [SerializeField] private SpriteRenderer slotRenderer;
        [SerializeField] private Color litColor = new Color(1f, 0.08f, 0.05f);
        [SerializeField] private Color unlitColor = new Color(0.18f, 0.02f, 0.025f);
        [SerializeField] private Color litSlotColor = new Color(0.42f, 0.04f, 0.045f);
        [SerializeField] private Color unlitSlotColor = new Color(0.08f, 0.08f, 0.11f);

        private PinballDropSlotRewardController controller;
        private bool lit;

        public bool IsLit => lit;

        public void Configure(
            PinballDropSlotRewardController owner,
            SpriteRenderer light,
            SpriteRenderer slot,
            Color activeLight,
            Color inactiveLight)
        {
            controller = owner;
            lightRenderer = light;
            slotRenderer = slot;
            litColor = activeLight;
            unlitColor = inactiveLight;
            SetLit(false);
        }

        public void SetLit(bool value)
        {
            lit = value;

            if (lightRenderer != null)
            {
                lightRenderer.color = lit ? litColor : unlitColor;
                lightRenderer.transform.localScale = Vector3.one * (lit ? 0.34f : 0.24f);
            }

            if (slotRenderer != null)
            {
                slotRenderer.color = lit ? litSlotColor : unlitSlotColor;
            }
        }

        private void Awake()
        {
            Collider2D trigger = GetComponent<Collider2D>();
            trigger.isTrigger = true;
        }

        private void OnTriggerEnter2D(Collider2D other)
        {
            if (other.GetComponent<PinballBall>() == null)
            {
                return;
            }

            controller?.ResolveSlot(this);
        }
    }
}
