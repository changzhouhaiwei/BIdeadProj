using UnityEngine;

namespace BallGame.Pinball
{
    public sealed class PinballPlunger : MonoBehaviour
    {
        [SerializeField] private KeyCode launchKey = KeyCode.Space;
        [SerializeField] private float minLaunchForce = 7f;
        [SerializeField] private float maxLaunchForce = 24f;
        [SerializeField] private float chargeSeconds = 1.2f;
        [SerializeField] private Vector2 launchDirection = Vector2.up;
        [SerializeField] private Transform plungerVisual;
        [SerializeField] private float visualTravel = 0.8f;
        [SerializeField] private AudioClip stressSound;
        [SerializeField] private AudioClip launchSound;

        private AudioSource audioSource;
        private Rigidbody2D ballInLane;
        private float charge;
        private Vector3 visualStartPosition;
        private bool stressPlayed;

        public void Configure(Transform visual, Vector2 direction, float minForce, float maxForce, AudioClip stress = null, AudioClip launch = null)
        {
            plungerVisual = visual;
            launchDirection = direction;
            minLaunchForce = minForce;
            maxLaunchForce = maxForce;
            stressSound = stress;
            launchSound = launch;
            visualStartPosition = plungerVisual != null ? plungerVisual.localPosition : Vector3.zero;
        }

        private void Awake()
        {
            audioSource = GetComponent<AudioSource>();
            if (plungerVisual != null)
            {
                visualStartPosition = plungerVisual.localPosition;
            }
        }

        private void Update()
        {
            if (Input.GetKey(launchKey))
            {
                charge = Mathf.Clamp01(charge + Time.deltaTime / Mathf.Max(0.01f, chargeSeconds));
                if (!stressPlayed)
                {
                    PlaySound(stressSound);
                    stressPlayed = true;
                }

                UpdateVisual();
                PinballGameController.Instance?.SetStatus($"Charging: {Mathf.RoundToInt(charge * 100f)}%");
                return;
            }

            if (Input.GetKeyUp(launchKey))
            {
                Release();
            }
        }

        private void OnTriggerEnter2D(Collider2D other)
        {
            TrackBall(other);
        }

        private void OnTriggerStay2D(Collider2D other)
        {
            TrackBall(other);
        }

        private void OnTriggerExit2D(Collider2D other)
        {
            if (other.attachedRigidbody == ballInLane)
            {
                ballInLane = null;
            }
        }

        private void TrackBall(Collider2D other)
        {
            PinballBall ball = other.GetComponent<PinballBall>();
            if (ball != null)
            {
                ballInLane = other.attachedRigidbody;
            }
        }

        private void Release()
        {
            if (ballInLane != null && charge > 0f)
            {
                float force = Mathf.Lerp(minLaunchForce, maxLaunchForce, charge);
                ballInLane.WakeUp();
                ballInLane.AddForce(launchDirection.normalized * force, ForceMode2D.Impulse);
                PinballGameController.Instance?.SetStatus($"Launch force: {force:0.0}");
                PlaySound(launchSound);
            }

            charge = 0f;
            stressPlayed = false;
            UpdateVisual();
        }

        private void UpdateVisual()
        {
            if (plungerVisual != null)
            {
                plungerVisual.localPosition = visualStartPosition + Vector3.down * (charge * visualTravel);
            }
        }

        private void PlaySound(AudioClip clip)
        {
            if (clip == null)
            {
                return;
            }

            if (audioSource == null)
            {
                audioSource = gameObject.AddComponent<AudioSource>();
            }

            audioSource.PlayOneShot(clip);
        }
    }
}
