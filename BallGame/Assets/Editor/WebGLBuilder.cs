using System.IO;
using System.Linq;
using UnityEditor;
using UnityEngine;

public static class WebGLBuilder
{
    public static void Build()
    {
        var outputPath = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "Builds", "WebGL"));
        Directory.CreateDirectory(outputPath);

        var scenes = EditorBuildSettings.scenes
            .Where(s => s.enabled && !string.IsNullOrEmpty(s.path))
            .Select(s => s.path)
            .ToArray();

        if (scenes.Length == 0)
        {
            Debug.LogError("WebGLBuilder: no enabled scenes in Build Settings.");
            EditorApplication.Exit(1);
            return;
        }

        Debug.Log($"WebGLBuilder: building {scenes.Length} scene(s) -> {outputPath}");

        var report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
        {
            scenes = scenes,
            locationPathName = outputPath,
            target = BuildTarget.WebGL,
            options = BuildOptions.None
        });

        var success = report != null
            && report.summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded;

        if (!success)
        {
            Debug.LogError($"WebGLBuilder: build failed: {report?.summary.result}");
            EditorApplication.Exit(1);
            return;
        }

        Debug.Log($"WebGLBuilder: success. size={report.summary.totalSize} bytes");
        EditorApplication.Exit(0);
    }
}
