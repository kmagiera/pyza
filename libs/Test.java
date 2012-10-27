

import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.lang.reflect.Method;
import java.util.*;

public class Test {

	public static class MyLoader extends ClassLoader {
		public Class<?> defineClass(byte[] data) {
			Class<?> clazz = defineClass(null, data, 0, data.length);
			resolveClass(clazz);
			return clazz;
		}
		public Class<?> loadClass(String name) throws ClassNotFoundException {
			System.out.println("Load " + name);
			Class<?> clazz = super.loadClass(name);
			System.out.println("LOADED");
			return clazz;
		}
		protected String findLibrary(String libname) {
			System.out.println("Find library " + libname);
			return super.findLibrary(libname);
		}
	}
	
	public static void main(String args[]) throws Exception {
		//byte[] data = getBytesFromFile(new File(args[0]));

		List<Class<?>> classes = new ArrayList<Class<?>>();
		MyLoader cl = new MyLoader();
		for (String file : args) {
			byte[] data = getBytesFromFile(new File(file));
			classes.add(cl.defineClass(data));
		}
		for (Class<?> clazz : classes) {
			Method mm = null;
			for (Method m : clazz.getMethods()) {
				if (m.getName().equals("main")) mm = m;
			}
			if (mm == null) continue;
			mm.setAccessible(true);
			System.err.println(mm.isAccessible());
			mm.invoke(null, (Object)(new String[] {}));
			System.err.println("END");
		}
	}

	public static byte[] getBytesFromFile(File file) throws IOException {
		InputStream is = new FileInputStream(file);
		long length = file.length();
		if (length > Integer.MAX_VALUE) {
		}
		byte[] bytes = new byte[(int) length];
		int offset = 0;
		int numRead = 0;
		while (offset < bytes.length
				&& (numRead = is.read(bytes, offset, bytes.length - offset)) >= 0) {
			offset += numRead;
		}
		if (offset < bytes.length) {
			throw new IOException("Could not completely read file "
					+ file.getName());
		}
		is.close();
		return bytes;
	}

}
