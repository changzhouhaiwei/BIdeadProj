using UnityEngine;

namespace BallGame.Pinball
{
    public sealed class PinballLoseZone : MonoBehaviour
    {
        [SerializeField] private AudioClip drainSound;

        private AudioSource audioSource;

        public void Configure(AudioClip sound)
        {
            drainSound = sound;
        }

        private void Awake()
        {
            audioSource = GetComponent<AudioSource>();
        }

        private void OnTriggerEnter2D(Collider2D other)
        {
            if (other.GetComponent<PinballBall>() != null)
            {
                PlaySound();
                PinballGameController.Instance?.DrainBall();
            }
        }

        private void PlaySound()
        {
            if (drainSound == null)
            {
                return;
            }

            if (audioSource == null)
            {
                audioSource = gameObject.AddComponent<AudioSource>();
            }

            audioSource.PlayOneShot(drainSound);
        }
    }
}
