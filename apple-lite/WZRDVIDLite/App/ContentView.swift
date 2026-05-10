import SwiftUI

struct ContentView: View {
    var body: some View {
        LiteWebView()
            .ignoresSafeArea(.container, edges: .bottom)
            .background(Color.black)
    }
}

#Preview {
    ContentView()
}
