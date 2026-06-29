using UnityEngine;

namespace BallGame.Pinball
{
    [RequireComponent(typeof(Rigidbody2D))]
    public sealed class PinballFlipper : MonoBehaviour
    {
        [SerializeField] private KeyCode primaryKey = KeyCode.A;
        [SerializeField] private KeyCode secondaryKey = KeyCode.LeftArrow;
        [SerializeField] private float restAngle;
        [SerializeField] private float activeAngle = 45f;
        [SerializeField] private float degreesPerSecond = 720f;
        [SerializeField] private AudioClip flipSound;

        private Rigidbody2D body2d;
        private AudioSource audioSource;
        private bool wasPressed;

        public void Configure(KeyCode primary, KeyCode secondary, float restRotation, float activeRotation, AudioClip sound = null)
        {
            primaryKey = primary;
            secondaryKey = secondary;
            restAngle = restRotation;
            activeAngle = activeRotation;
            flipSound = sound;
        }

        private void Awake()
        {
            body2d = GetComponent<Rigidbody2D>();
            body2d.bodyType = RigidbodyType2D.Kinematic;
            body2d.interpolation = RigidbodyInterpolation2D.Interpolate;
            audioSource = GetComponent<AudioSource>();
        }

        private void FixedUpdate()
        {
            bool pressed = Input.GetKey(primaryKey) || Input.GetKey(secondaryKey);
            if (pressed && !wasPressed)
            {
                PlaySound();
            }

            float targetAngle = pressed ? activeAngle : restAngle;
            float nextAngle = Mathf.MoveTowardsAngle(body2d.rotation, targetAngle, degreesPerSecond * Time.fixedDeltaTime);
            body2d.MoveRotation(nextAngle);
            wasPressed = pressed;
        }

        private void PlaySound()
        {
            if (flipSound == null)
            {
                return;
            }

            if (audioSource == null)
            {
                audioSource = gameObject.AddComponent<AudioSource>();
            }

            audioSource.PlayOneShot(flipSound);
        }
    }
}
